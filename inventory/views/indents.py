import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import DatabaseError, transaction, connection
from django.db.models import BooleanField, Case, Q, Value, When
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from ..forms.indent_forms import IndentForm, IndentItemFormSet
from ..indent_pdf import generate_indent_pdf
from ..models import Indent, Department

logger = logging.getLogger(__name__)

BADGE_BASE = "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"

INDENT_STATUS_BADGES = {
    "PENDING": f"{BADGE_BASE} bg-warning-light text-warning",
    "APPROVED": f"{BADGE_BASE} bg-success-light text-success",
    "SUBMITTED": f"{BADGE_BASE} bg-warning-light text-warning",
    "PROCESSING": f"{BADGE_BASE} bg-warning-light text-warning",
    "COMPLETED": f"{BADGE_BASE} bg-success-light text-success",
    "CANCELLED": f"{BADGE_BASE} bg-red-100 text-red-700",
}


class IndentsListView(TemplateView):
    """Show search and filter options for indents.

    GET params:
        status: filter by indent status.
        q: search term for MRN, requester or department.
    Template: inventory/indents_list.html.
    """

    template_name = "inventory/indents_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        status = (self.request.GET.get("status") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        total_indents = Indent.objects.count()
        filters = [
            {
                "name": "status",
                "value": status,
                "list_id": "indent-statuses",
                "options": [
                    {"value": "", "label": "All Statuses"},
                    {"value": "SUBMITTED", "label": "Submitted"},
                    {"value": "PROCESSING", "label": "Processing"},
                    {"value": "COMPLETED", "label": "Completed"},
                    {"value": "CANCELLED", "label": "Cancelled"},
                ],
            }
        ]
        ctx.update(
            {
                "status": status,
                "q": q,
                "total_indents": total_indents,
                "filters": filters,
                "quick_form": IndentForm(),
                "list_url": reverse("root"),
                "list_title": "Dashboard",
                "current_title": "Indents",
            }
        )
        return ctx

    def post(self, request, *args, **kwargs):
        """Handle quick indent submission without line items."""

        form = IndentForm(request.POST)
        if form.is_valid():
            indent = form.save()
            messages.success(request, "Indent submitted")
            return redirect("indent_detail", pk=indent.pk)

        ctx = self.get_context_data(**kwargs)
        ctx["quick_form"] = form
        return render(request, self.template_name, ctx)


class IndentsTableView(TemplateView):
    """Render the paginated table of indents.

    GET params:
        status and q: same filters as the list view.
        page: page number for pagination.
    Template: inventory/_indents_table.html.
    """

    template_name = "inventory/_indents_table.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        status = (self.request.GET.get("status") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        qs = Indent.objects.all()
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(mrn__icontains=q)
                | Q(requested_by__icontains=q)
                | Q(department__name__icontains=q)
            )
        today = timezone.now().date()
        qs = qs.annotate(
            is_overdue=Case(
                When(
                    Q(date_required__lt=today)
                    & ~Q(status__in=["COMPLETED", "APPROVED"]),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            )
        ).order_by("-indent_id")
        paginator = Paginator(qs, 25)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        ctx.update(
            {
                "page_obj": page_obj,
                "status": status,
                "q": q,
                "badges": INDENT_STATUS_BADGES,
            }
        )
        return ctx


class IndentCreateView(View):
    """Handle creation of a new indent with item lines.

    GET renders an empty indent form and formset.
    POST expects IndentForm and IndentItemFormSet data.
    Template: inventory/indent_form.html.
    """

    template_name = "inventory/indent_form.html"
    partial_template = "inventory/_indent_create_partial.html"

    def get(self, request):
        form = IndentForm()
        suggest_url = reverse("item_search")
        formset = IndentItemFormSet(prefix="items", form_kwargs={"item_suggest_url": suggest_url})
        # Pre-fill requested_by from logged-in user; keep hidden in form
        try:
            rb = (
                (getattr(request.user, "get_full_name", lambda: "")() or None)
                or getattr(request.user, "username", None)
                or getattr(request.user, "email", None)
            )
        except Exception:
            rb = None
        if rb and "requested_by" in form.fields:
            form.fields["requested_by"].initial = rb
        # Provide department options for datalist
        try:
            dept_options = list(
                Department.objects.only("department_id", "name").order_by("name").values_list("department_id", "name")
            )
        except Exception:
            dept_options = []
        ctx = {"form": form, "formset": formset, "department_options": dept_options, "requested_by_display": rb}
        if (request.GET.get("partial") or "").lower() in {"1", "true", "yes"}:
            return render(request, self.partial_template, ctx)
        # No full-page create form; surface only via modal/drawer
        raise Http404("Indent creation is available via the modal only.")

    def post(self, request):
        form = IndentForm(request.POST)
        suggest_url = reverse("item_search")
        formset = IndentItemFormSet(request.POST, prefix="items", form_kwargs={"item_suggest_url": suggest_url})
        is_partial = (request.POST.get("partial") or "").lower() in {"1", "true", "yes"}
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    indent = form.save(commit=False)
                    # Normalize department: if UI posted an ID, convert to name for ORM save
                    dep_raw = (
                        request.POST.get("department")
                        or request.POST.get("id_department")
                        or request.POST.get("department-ui")
                        or ""
                    )
                    if str(dep_raw).isdigit():
                        try:
                            dep_obj = Department.objects.only("name").get(pk=int(dep_raw))
                            indent.department = dep_obj.name
                        except Exception:
                            pass
                    # Fill requested_by if not provided
                    if not indent.requested_by:
                        try:
                            rb = (
                                (getattr(request.user, "get_full_name", lambda: "")() or None)
                                or getattr(request.user, "username", None)
                                or getattr(request.user, "email", None)
                            )
                        except Exception:
                            rb = None
                        indent.requested_by = rb or indent.requested_by or ""
                    # Use a savepoint so we can gracefully recover from schema errors
                    sp_id = transaction.savepoint()
                    try:
                        indent.save()
                        indent_pk = indent.pk
                        transaction.savepoint_commit(sp_id)
                    except DatabaseError as save_err:
                        # Roll back to the savepoint to clear the transaction state
                        transaction.savepoint_rollback(sp_id)
                        # Fallback: older schema uses department_id (FK) instead of text column
                        # If the error complains about missing "department" column, insert manually
                        msg = str(save_err).lower()
                        if "column \"department\"" in msg and "relation \"indents\"" in msg and "does not exist" in msg:
                            # Resolve department id from provided value or name; fallback to 'General'
                            dep_raw = (
                                request.POST.get("department")
                                or request.POST.get("id_department")
                                or request.POST.get("department-ui")
                                or getattr(indent, "department", None)
                                or "General"
                            )
                            dept_id = None
                            try:
                                if str(dep_raw).isdigit():
                                    dept = Department.objects.get(pk=int(dep_raw))
                                    dept_id = dept.pk
                                else:
                                    dept, _ = Department.objects.get_or_create(name=str(dep_raw) or "General")
                                    dept_id = dept.pk
                            except Exception:
                                dept_id = None
                            # Build manual insert
                            with connection.cursor() as cur:
                                cur.execute(
                                    """
                                    INSERT INTO indents (mrn, requested_by, date_required, status, notes, department_id, created_at, updated_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                                    RETURNING indent_id
                                    """,
                                    [
                                        indent.mrn,
                                        indent.requested_by or "",
                                        getattr(indent, "date_required", None),
                                        indent.status or "Submitted",
                                        getattr(indent, "notes", "") or "",
                                        dept_id,
                                    ],
                                )
                                indent_pk = cur.fetchone()[0]
                            # Create a lightweight instance for the formset
                            indent = Indent(indent_id=indent_pk)
                        else:
                            # Unexpected DB error: re-raise so outer handler can report properly
                            raise

                    formset.instance = indent
                    formset.save()
                if is_partial:
                    from django.http import JsonResponse

                    return JsonResponse(
                        {"ok": True, "message": f"Indent {getattr(indent, 'mrn', '')} created", "id": indent.pk}
                    )
                return redirect("indent_detail", pk=indent.pk)
            except DatabaseError as e:
                if is_partial:
                    from django.http import JsonResponse

                    return JsonResponse(
                        {"ok": False, "message": f"Unable to save indent: {e}"}, status=400
                    )
                messages.error(request, "Unable to save indent")
        if is_partial:
            from django.http import JsonResponse

            # Combine first form error into a simple string, if any
            err_msg = "Validation error"
            try:
                if form.errors:
                    # Join first errors per field for better visibility
                    err_msg = "; ".join(
                        [f"{k}: {v[0]}" for k, v in form.errors.items() if v]
                    )
                elif any(formset.errors):
                    # Collect first row's errors
                    for i, ferr in enumerate(formset.errors):
                        if ferr:
                            first_key = next(iter(ferr))
                            err_msg = f"Row {i+1} - {first_key}: {ferr[first_key][0]}"
                            break
                elif formset.non_form_errors():
                    err_msg = "; ".join(formset.non_form_errors())
            except Exception:
                pass
            return JsonResponse({"ok": False, "message": str(err_msg)}, status=400)
        # Provide department options again on normal render
        try:
            dept_options = list(
                Department.objects.only("department_id", "name").order_by("name").values_list("department_id", "name")
            )
        except Exception:
            dept_options = []
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "department_options": dept_options,
                "requested_by_display": form.data.get("requested_by", ""),
            },
        )


def indent_detail(request, pk: int):
    indent = get_object_or_404(Indent, pk=pk)
    items = indent.indentitem_set.select_related("item").all()
    badge_class = INDENT_STATUS_BADGES.get(indent.status.upper(), "")
    rows = [
        (
            "Status",
            format_html(
                '<span class="px-2 py-1 rounded {}">{}</span>',
                badge_class,
                indent.status,
            ),
        ),
        ("Requested By", indent.requested_by),
        ("Department", indent.department),
    ]
    # Prepare WhatsApp message URL with basic details
    try:
        from urllib.parse import quote_plus

        wa_text = (
            f"Indent Submitted:\nMRN: {indent.mrn or indent.pk}\n"
            f"Requested By: {indent.requested_by or ''}\n"
            f"Department: {indent.department or ''}\n"
            f"Date Required: {getattr(indent, 'date_required', '')}"
        )
        wa_url = f"https://wa.me/?text={quote_plus(wa_text)}"
    except Exception:
        wa_url = None
    ctx = {"indent": indent, "items": items, "rows": rows, "wa_url": wa_url}
    return render(request, "inventory/indent_detail.html", ctx)


@require_POST
@csrf_protect
def indent_update_status(request, pk: int, status: str):
    indent = get_object_or_404(Indent, pk=pk)
    indent.status = status.upper()
    indent.save()
    return redirect("indent_detail", pk=pk)


def indent_pdf(request, pk: int):
    indent = get_object_or_404(Indent, pk=pk)
    items = indent.indentitem_set.select_related("item").all()
    pdf_bytes = generate_indent_pdf(indent, items)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    filename = f"indent_{indent.pk}.pdf"
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response
