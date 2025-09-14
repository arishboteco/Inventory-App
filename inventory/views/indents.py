import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import DatabaseError, transaction, connection, IntegrityError
from django.db.models import BooleanField, Case, Q, Value, When
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from ..forms.indent_forms import IndentForm, IndentItemFormSet
from ..services import list_utils
from ..indent_pdf import generate_indent_pdf
from ..models import Department, Indent

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
        dept = (self.request.GET.get("department") or "").strip()
        requested_by = (self.request.GET.get("requested_by") or "").strip()
        start_date = (self.request.GET.get("start") or "").strip()
        end_date = (self.request.GET.get("end") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        total_indents = Indent.objects.count()
        # Build filter options for the filter bar
        dept_options = (
            Department.objects.only("department_id", "name")
            .order_by("name")
            .values_list("department_id", "name")
        )
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
            },
            {
                "name": "department",
                "label": "Department",
                "value": dept,
                "options": ([{"value": "", "label": "All Departments"}] + [
                    {"value": str(did), "label": name} for did, name in dept_options
                ]),
            },
            {
                "name": "requested_by",
                "label": "Requested By",
                "value": requested_by,
                "options": [
                    {"value": "", "label": "All Requesters"},
                    {"value": "admin", "label": "admin"},
                    {"value": "testuser", "label": "testuser"},
                ],
            },
        ]
        ctx.update(
            {
                "status": status,
                "department": dept,
                "requested_by": requested_by,
                "start": start_date,
                "end": end_date,
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
        # Base queryset with overdue annotation
        today = timezone.now().date()
        qs = Indent.objects.all().annotate(
            is_overdue=Case(
                When(
                    Q(date_required__lt=today)
                    & ~Q(status__in=["COMPLETED", "APPROVED"]),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            )
        )

        # Apply search, filters, and sorting using shared utils
        qs, params = list_utils.apply_filters_sort(
            self.request,
            qs,
            search_fields=["mrn", "requested_by", "department__name"],
            filter_fields={
                "status": "status",
                "department": "department_id",
                "requested_by": "requested_by__iexact",
                "start": "date_required__gte",
                "end": "date_required__lte",
            },
            allowed_sorts=[
                "indent_id",
                "mrn",
                "requested_by",
                "department__name",
                "status",
                "date_required",
            ],
            default_sort="mrn",
            default_direction="desc",
        )
        paginator = Paginator(qs, 25)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        # Build querystring for header sort links and pagination without page
        try:
            querystring = list_utils.build_querystring(self.request)
        except Exception:
            querystring = ""
        ctx.update({
            "page_obj": page_obj,
            "badges": INDENT_STATUS_BADGES,
            "querystring": querystring,
            **params,
        })
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
            stage = "pre"
            try:
                # Perform all DB writes inside a single atomic block; if anything fails,
                # the exception will unwind to this except and the block will be rolled back.
                with transaction.atomic():
                    indent = form.save(commit=False)
                    # Normalize department: map UI value to FK
                    dep_raw = (
                        request.POST.get("department")
                        or request.POST.get("id_department")
                        or request.POST.get("department-ui")
                        or ""
                    )
                    # If no department is provided at all, fail early with a friendly message
                    if not str(dep_raw).strip():
                        if is_partial:
                            from django.http import JsonResponse
                            return JsonResponse({"ok": False, "message": "Please select a department"}, status=400)
                        messages.error(request, "Please select a department")
                        return render(request, self.template_name, {"form": form, "formset": formset})
                    if str(dep_raw).isdigit():
                        # Validate that department exists to avoid FK DB errors later
                        try:
                            dep_id = int(dep_raw)
                        except Exception:
                            dep_id = None
                        if dep_id is not None and Department.objects.filter(pk=dep_id).exists():
                            indent.department_id = dep_id
                        else:
                            if is_partial:
                                from django.http import JsonResponse

                                return JsonResponse({
                                    "ok": False,
                                    "message": "Please select a valid department",
                                }, status=400)
                            messages.error(request, "Please select a valid department")
                            return render(request, self.template_name, {"form": form, "formset": formset})
                    elif dep_raw:
                        try:
                            indent.department = Department.objects.get(name=dep_raw)
                        except Department.DoesNotExist:
                            indent.department = None
                    # After normalization, ensure we have a department set prior to saving
                    if not getattr(indent, "department_id", None) and not getattr(indent, "department", None):
                        if is_partial:
                            from django.http import JsonResponse

                            return JsonResponse({"ok": False, "message": "Please select a valid department"}, status=400)
                        messages.error(request, "Please select a valid department")
                        return render(request, self.template_name, {"form": form, "formset": formset})
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

                    # Save with retry on MRN unique conflicts
                    stage = "indent_save"
                    try:
                        indent.save()
                    except IntegrityError:
                        # Likely MRN collision with existing data; regenerate a unique MRN and retry once
                        try:
                            # Time-based unique MRN fallback
                            ts = timezone.now().strftime("%Y%m%d%H%M%S%f")
                            indent.mrn = f"MRN-{ts}"
                        except Exception:
                            indent.mrn = f"MRN-{int(timezone.now().timestamp())}"
                        indent.save()
                    stage = "formset_save"
                    formset.instance = indent
                    formset.save()

                if is_partial:
                    from django.http import JsonResponse

                    return JsonResponse(
                        {"ok": True, "message": f"Indent {getattr(indent, 'mrn', '')} created", "id": indent.pk}
                    )
                return redirect("indent_detail", pk=indent.pk)
            except DatabaseError as db_ex:
                # Attempt a compatibility fallback for environments where the indents table
                # has older columns (e.g., 'department' text instead of 'department_id').
                try:
                    # If this looks like a missing/invalid department, short-circuit with a friendly message
                    msg_text = str(db_ex) if db_ex else ""
                    if is_partial and (
                        "department" in msg_text.lower()
                        and ("null" in msg_text.lower() or "foreign key" in msg_text.lower() or "invalid" in msg_text.lower())
                    ):
                        from django.http import JsonResponse
                        return JsonResponse({"ok": False, "message": "Please select a valid department"}, status=400)
                    # If failure happened during line items save, do NOT fallback insert; ensure atomicity
                    if 'stage' in locals() and stage == "formset_save":
                        raise
                    # Gather raw values we can use for a manual insert
                    dep_raw = (
                        request.POST.get("department")
                        or request.POST.get("id_department")
                        or request.POST.get("department-ui")
                        or ""
                    )
                    # Build a snapshot of the object without hitting the DB again
                    obj = form.save(commit=False)
                    if not getattr(obj, "mrn", None):
                        # Reuse the save() generator logic indirectly by calling form.save(commit=False) earlier
                        pass
                    # Resolve department display name if only a text column exists
                    dept_name = None
                    if str(dep_raw).isdigit():
                        try:
                            d = Department.objects.only("name").get(pk=int(dep_raw))
                            dept_name = d.name
                        except Exception:
                            dept_name = None
                    elif dep_raw:
                        dept_name = str(dep_raw)

                    # If we still don't have any department info, abort with a friendly message
                    if not dept_name and not (str(dep_raw).isdigit() and Department.objects.filter(pk=int(dep_raw)).exists()):
                        raise ValueError("Invalid department")

                    # One atomic block to ensure all-or-nothing
                    with transaction.atomic():
                        with connection.cursor() as cur:
                            # Discover actual columns present
                            table = "indents"
                            cols = {c.name for c in connection.introspection.get_table_description(cur, table)}
                            # Determine primary key column name if possible
                            pk_col = "indent_id" if "indent_id" in cols else ("id" if "id" in cols else None)
                            insert_cols = []
                            params = []
                            # Portable timestamps
                            now = timezone.now()
                            # Core fields
                            if "mrn" in cols:
                                insert_cols.append("mrn")
                                params.append(getattr(obj, "mrn", None))
                            if "requested_by" in cols:
                                insert_cols.append("requested_by")
                                params.append(getattr(obj, "requested_by", "") or "")
                            if "date_required" in cols:
                                insert_cols.append("date_required")
                                params.append(getattr(obj, "date_required", None))
                            if "status" in cols:
                                insert_cols.append("status")
                                params.append(getattr(obj, "status", "SUBMITTED") or "SUBMITTED")
                            if "notes" in cols:
                                insert_cols.append("notes")
                                params.append(getattr(obj, "notes", "") or "")
                            # Department compatibility: prefer FK if present, else name
                            dept_id_val = None
                            try:
                                if str(dep_raw).isdigit():
                                    dept_id_val = int(dep_raw)
                                elif dep_raw:
                                    d = Department.objects.only("department_id").get(name=str(dep_raw))
                                    dept_id_val = d.pk
                            except Exception:
                                dept_id_val = None
                            if "department_id" in cols:
                                insert_cols.append("department_id")
                                params.append(dept_id_val)
                            elif "department" in cols:
                                insert_cols.append("department")
                                params.append(dept_name or "")
                            # Timestamps if present
                            if "created_at" in cols:
                                insert_cols.append("created_at")
                                params.append(now)
                            if "updated_at" in cols:
                                insert_cols.append("updated_at")
                                params.append(now)

                            if not insert_cols:
                                raise

                            # Build portable INSERT
                            col_sql = ", ".join(insert_cols)
                            placeholders = ", ".join(["%s"] * len(insert_cols))
                            vendor = connection.vendor

                            if vendor == "postgresql" and pk_col:
                                cur.execute(
                                    f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders}) RETURNING {pk_col}",
                                    params,
                                )
                                new_id = cur.fetchone()[0]
                            else:
                                cur.execute(
                                    f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})",
                                    params,
                                )
                                try:
                                    new_id = cur.lastrowid
                                except Exception:
                                    # Fallback best-effort: last inserted PK
                                    if not pk_col:
                                        raise
                                    cur2 = connection.cursor()
                                    try:
                                        cur2.execute(f"SELECT MAX({pk_col}) FROM {table}")
                                        new_id = cur2.fetchone()[0]
                                    finally:
                                        cur2.close()

                        # Proceed to save formset rows pointing to this indent
                        compat_indent = Indent(indent_id=new_id)
                        formset.instance = compat_indent
                        formset.save()

                    if is_partial:
                        from django.http import JsonResponse

                        return JsonResponse(
                            {"ok": True, "message": f"Indent {getattr(obj, 'mrn', '')} created", "id": new_id}
                        )
                    return redirect("indent_detail", pk=new_id)
                except Exception as ex:
                    # Ensure we report a friendly message and avoid leaking the atomic error
                    logger.exception("Database error while creating indent")
                    if is_partial:
                        from django.http import JsonResponse
                        # Map common DB errors to actionable messages; include raw text only in DEBUG
                        raw = str(ex) if ex else ""
                        friendly = None
                        low = raw.lower()
                        if "foreign key" in low or ("department" in low and ("null" in low or "invalid" in low)):
                            friendly = "Please select a valid department"
                        elif "unique" in low and "mrn" in low:
                            friendly = "MRN already exists. Please try again."
                        from django.conf import settings
                        message = friendly or (raw if getattr(settings, 'DEBUG', False) else "Unable to save indent due to a database error. Please try again.")
                        return JsonResponse({"ok": False, "message": message}, status=400)
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
    # Support modal/drawer partial render
    if (request.GET.get("partial") or "").lower() in {"1", "true", "yes"}:
        return render(request, "inventory/_indent_detail_partial.html", ctx)
    return render(request, "inventory/indent_detail.html", ctx)


@require_POST
@csrf_protect
def indent_update_status(request, pk: int, status: str):
    indent = get_object_or_404(Indent, pk=pk)
    indent.status = status.upper()
    indent.save()
    # If HTMX request, return the updated table fragment to stay on the same page
    if request.headers.get("HX-Request"):
        # Reuse the table view logic to render current filtered/sorted list
        view = IndentsTableView()
        view.request = request
        ctx = view.get_context_data()
        return render(request, view.template_name, ctx)
    return redirect("indent_detail", pk=pk)


def indent_pdf(request, pk: int):
    indent = get_object_or_404(Indent, pk=pk)
    items = indent.indentitem_set.select_related("item").all()
    pdf_bytes = generate_indent_pdf(indent, items)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    mrn = getattr(indent, "mrn", None) or str(indent.pk)
    # Normalize spacing and enforce desired naming scheme
    safe_mrn = str(mrn).replace("/", "-").replace(" ", "")
    filename = f"Indent_{safe_mrn}.pdf"
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response
