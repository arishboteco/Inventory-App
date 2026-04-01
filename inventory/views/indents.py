import logging
import uuid

from django import forms
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.models import BooleanField, Case, DecimalField, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce
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
from ..forms.indent_issue_forms import IndentIssueFormset, IndentItemIssueForm
from ..indent_pdf import generate_indent_pdf
from ..models import Department, Indent, Item
from ..models import IndentItem as IndentItemModel
from ..models import Supplier as SupplierModel
from ..services import indent_consolidation_service, indent_issue_service, list_utils

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
        approved_count = Indent.objects.filter(status__iexact="APPROVED").count()
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
                    {"value": "PENDING", "label": "Pending"},
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
                "options": (
                    [{"value": "", "label": "All Departments"}]
                    + [{"value": str(did), "label": name} for did, name in dept_options]
                ),
            },
            {
                "name": "requested_by",
                "label": "Requested By",
                "value": requested_by,
                "options": [{"value": "", "label": "All Requesters"}]
                + [
                    {"value": u, "label": u}
                    for u in Indent.objects.exclude(requested_by="")
                    .exclude(requested_by__isnull=True)
                    .values_list("requested_by", flat=True)
                    .distinct()
                    .order_by("requested_by")
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
                "approved_count": approved_count,
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
            messages.success(request, "Indent submitted", extra_tags="toast")
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
        # Base queryset with related data and overdue annotation
        today = timezone.now().date()
        qs = Indent.objects.select_related("department", "source_recipe").annotate(
            is_overdue=Case(
                When(
                    Q(date_required__lt=today)
                    & ~Q(status__in=["COMPLETED", "APPROVED"]),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
        try:
            zero = Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
            qs = qs.annotate(
                req_total=Coalesce(Sum("indentitem__requested_qty"), zero),
                iss_total=Coalesce(Sum("indentitem__issued_qty"), zero),
            )
        except Exception:
            logger.exception(
                "Failed to annotate indent totals; continuing without totals"
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
        ctx.update(
            {
                "page_obj": page_obj,
                "badges": INDENT_STATUS_BADGES,
                "querystring": querystring,
                **params,
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
        formset = IndentItemFormSet(
            prefix="items", form_kwargs={"item_suggest_url": suggest_url}
        )
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
                Department.objects.only("department_id", "name")
                .order_by("name")
                .values_list("department_id", "name")
            )
        except Exception:
            dept_options = []
        ctx = {
            "form": form,
            "formset": formset,
            "department_options": dept_options,
            "requested_by_display": rb,
        }
        if (request.GET.get("partial") or "").lower() in {"1", "true", "yes"}:
            return render(request, self.partial_template, ctx)
        # No full-page create form; surface only via modal/drawer
        raise Http404("Indent creation is available via the modal only.")

    def post(self, request):
        form = IndentForm(request.POST)
        suggest_url = reverse("item_search")
        formset = IndentItemFormSet(
            request.POST, prefix="items", form_kwargs={"item_suggest_url": suggest_url}
        )
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

                            return JsonResponse(
                                {"ok": False, "message": "Please select a department"},
                                status=400,
                            )
                        messages.error(
                            request, "Please select a department", extra_tags="toast"
                        )
                        return render(
                            request,
                            self.template_name,
                            {"form": form, "formset": formset},
                        )
                    if str(dep_raw).isdigit():
                        # Validate that department exists to avoid FK DB errors later
                        try:
                            dep_id = int(dep_raw)
                        except Exception:
                            dep_id = None
                        if (
                            dep_id is not None
                            and Department.objects.filter(pk=dep_id).exists()
                        ):
                            indent.department_id = dep_id
                        else:
                            if is_partial:
                                from django.http import JsonResponse

                                return JsonResponse(
                                    {
                                        "ok": False,
                                        "message": "Please select a valid department",
                                    },
                                    status=400,
                                )
                            messages.error(
                                request,
                                "Please select a valid department",
                                extra_tags="toast",
                            )
                            return render(
                                request,
                                self.template_name,
                                {"form": form, "formset": formset},
                            )
                    elif dep_raw:
                        try:
                            indent.department = Department.objects.get(name=dep_raw)
                        except Department.DoesNotExist:
                            indent.department = None
                    # After normalization, ensure we have a department set prior to saving
                    if not getattr(indent, "department_id", None) and not getattr(
                        indent, "department", None
                    ):
                        if is_partial:
                            from django.http import JsonResponse

                            return JsonResponse(
                                {
                                    "ok": False,
                                    "message": "Please select a valid department",
                                },
                                status=400,
                            )
                        messages.error(
                            request,
                            "Please select a valid department",
                            extra_tags="toast",
                        )
                        return render(
                            request,
                            self.template_name,
                            {"form": form, "formset": formset},
                        )
                    # Fill requested_by if not provided
                    if not indent.requested_by:
                        try:
                            rb = (
                                (
                                    getattr(request.user, "get_full_name", lambda: "")()
                                    or None
                                )
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
                        {
                            "ok": True,
                            "message": f"Indent {getattr(indent, 'mrn', '')} created",
                            "toast_message": f"Indent {getattr(indent, 'mrn', '')} created",
                            "id": indent.pk,
                            "reload": {
                                "url": reverse("indents_table"),
                                "target": "#indents_table",
                            },
                        }
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
                        and (
                            "null" in msg_text.lower()
                            or "foreign key" in msg_text.lower()
                            or "invalid" in msg_text.lower()
                        )
                    ):
                        from django.http import JsonResponse

                        return JsonResponse(
                            {
                                "ok": False,
                                "message": "Please select a valid department",
                            },
                            status=400,
                        )
                    # If failure happened during line items save, do NOT fallback insert; ensure atomicity
                    if "stage" in locals() and stage == "formset_save":
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
                    if not dept_name and not (
                        str(dep_raw).isdigit()
                        and Department.objects.filter(pk=int(dep_raw)).exists()
                    ):
                        raise ValueError("Invalid department")

                    # One atomic block to ensure all-or-nothing
                    with transaction.atomic():
                        with connection.cursor() as cur:
                            # Discover actual columns present
                            table = "indents"
                            cols = {
                                c.name
                                for c in connection.introspection.get_table_description(
                                    cur, table
                                )
                            }
                            # Determine primary key column name if possible
                            pk_col = (
                                "indent_id"
                                if "indent_id" in cols
                                else ("id" if "id" in cols else None)
                            )
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
                                params.append(
                                    getattr(obj, "status", "SUBMITTED") or "SUBMITTED"
                                )
                            if "notes" in cols:
                                insert_cols.append("notes")
                                params.append(getattr(obj, "notes", "") or "")
                            # Department compatibility: prefer FK if present, else name
                            dept_id_val = None
                            try:
                                if str(dep_raw).isdigit():
                                    dept_id_val = int(dep_raw)
                                elif dep_raw:
                                    d = Department.objects.only("department_id").get(
                                        name=str(dep_raw)
                                    )
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

                            # Build portable INSERT — quote all identifiers
                            q_table = f'"{table}"'
                            q_cols = ", ".join(f'"{c}"' for c in insert_cols)
                            placeholders = ", ".join(["%s"] * len(insert_cols))
                            vendor = connection.vendor

                            if vendor == "postgresql" and pk_col:
                                q_pk = f'"{pk_col}"'
                                cur.execute(
                                    f"INSERT INTO {q_table} ({q_cols}) VALUES ({placeholders}) RETURNING {q_pk}",
                                    params,
                                )
                                new_id = cur.fetchone()[0]
                            else:
                                cur.execute(
                                    f"INSERT INTO {q_table} ({q_cols}) VALUES ({placeholders})",
                                    params,
                                )
                                try:
                                    new_id = cur.lastrowid
                                except Exception:
                                    # Fallback best-effort: last inserted PK
                                    if not pk_col:
                                        raise
                                    q_pk = f'"{pk_col}"'
                                    cur2 = connection.cursor()
                                    try:
                                        cur2.execute(
                                            f"SELECT MAX({q_pk}) FROM {q_table}"
                                        )
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
                            {
                                "ok": True,
                                "message": f"Indent {getattr(obj, 'mrn', '')} created",
                                "toast_message": f"Indent {getattr(obj, 'mrn', '')} created",
                                "id": new_id,
                                "reload": {
                                    "url": reverse("indents_table"),
                                    "target": "#indents_table",
                                },
                            }
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
                        if "foreign key" in low or (
                            "department" in low and ("null" in low or "invalid" in low)
                        ):
                            friendly = "Please select a valid department"
                        elif "unique" in low and "mrn" in low:
                            friendly = "MRN already exists. Please try again."
                        from django.conf import settings

                        message = friendly or (
                            raw
                            if getattr(settings, "DEBUG", False)
                            else "Unable to save indent due to a database error. Please try again."
                        )
                        return JsonResponse(
                            {"ok": False, "message": message}, status=400
                        )
                    messages.error(request, "Unable to save indent", extra_tags="toast")
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
                            err_msg = f"Row {i + 1} - {first_key}: {ferr[first_key][0]}"
                            break
                elif formset.non_form_errors():
                    err_msg = "; ".join(formset.non_form_errors())
            except Exception:
                pass
            return JsonResponse({"ok": False, "message": str(err_msg)}, status=400)
        # Provide department options again on normal render
        try:
            dept_options = list(
                Department.objects.only("department_id", "name")
                .order_by("name")
                .values_list("department_id", "name")
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
    items = (
        indent.indentitem_set.select_related("item")
        .prefetch_related(
            "po_links", "po_links__po_item", "po_links__po_item__purchase_order"
        )
        .all()
    )
    # Compute remaining quantity for display
    try:
        from decimal import Decimal

        # Lazy import to avoid circulars at module import time
        from ..services.units_service import UnitsService  # type: ignore

        units_map = {
            u["unit_id"]: u["purchase_unit"] for u in UnitsService.get_all_units()
        }
        for it in items:
            rq = Decimal(str(getattr(it, "requested_qty", 0) or 0))
            iq = Decimal(str(getattr(it, "issued_qty", 0) or 0))
            remaining = rq - iq
            if remaining < 0:
                remaining = Decimal("0")
            it.remaining_qty = remaining
            try:
                unit_id = getattr(getattr(it, "item", None), "unit_id", None)
                it.unit_display = (
                    units_map.get(int(unit_id), "") if unit_id is not None else ""
                )
            except Exception:
                it.unit_display = ""
    except Exception:
        for it in items:
            it.remaining_qty = getattr(it, "requested_qty", 0)
            it.unit_display = ""
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
    # Prepare WhatsApp message URL with status and item details
    try:
        from urllib.parse import quote_plus

        status_label = indent.get_status_display()
        items_lines = "\n".join(
            "- {}: {} {}".format(
                ii.item.name if ii.item else "?",
                ii.requested_qty,
                ii.unit_display or "",
            ).rstrip()
            for ii in items
        )
        wa_text = (
            f"Indent: {indent.mrn or indent.pk}\n"
            f"Status: {status_label}\n"
            f"Department: {indent.department or ''}\n"
            f"Date Required: {getattr(indent, 'date_required', '')}\n"
            f"Requested By: {indent.requested_by or ''}\n"
            f"\nItems:\n{items_lines or '(none)'}"
        )
        wa_url = f"https://wa.me/?text={quote_plus(wa_text)}"
    except Exception:
        wa_url = None
    # Compute overdue flag for the detail template
    try:
        _today = timezone.now().date()
        is_overdue = (
            getattr(indent, "date_required", None) is not None
            and indent.date_required < _today
            and indent.status.upper() not in ("COMPLETED", "CANCELLED")
        )
    except Exception:
        is_overdue = False
    edit_mode = request.GET.get("edit") == "1"
    # Only SUBMITTED or APPROVED indents can be edited
    if edit_mode and indent.status.upper() not in {"SUBMITTED", "APPROVED"}:
        edit_mode = False
    department_options = []
    if edit_mode:
        try:
            department_options = list(
                Department.objects.only("department_id", "name")
                .order_by("name")
                .values_list("department_id", "name")
            )
        except Exception:
            department_options = []
    ctx = {
        "indent": indent,
        "items": items,
        "rows": rows,
        "wa_url": wa_url,
        "is_overdue": is_overdue,
        "has_po_links": any(ii.po_links.exists() for ii in items),
        "list_url": reverse("indents_list"),
        "list_title": "Indents",
        "current_title": f"Indent {indent.mrn or indent.pk}",
        "edit_mode": edit_mode,
        "department_options": department_options,
    }
    # Support modal/drawer partial render
    if (request.GET.get("partial") or "").lower() in {"1", "true", "yes"}:
        return render(request, "inventory/_indent_detail_partial.html", ctx)
    return render(request, "inventory/indent_detail.html", ctx)


class IndentUpdateView(View):
    """Handle updates to an existing indent (department, date_required, notes)."""

    def post(self, request, pk: int):
        from datetime import date as date_type

        indent = get_object_or_404(Indent, pk=pk)
        if indent.status.upper() not in {"SUBMITTED", "APPROVED"}:
            messages.warning(
                request,
                "Only submitted or approved indents can be edited.",
                extra_tags="toast",
            )
            return redirect("indent_detail", pk=pk)

        update_fields = ["updated_at"]

        # Department
        dep_raw = request.POST.get("department", "").strip()
        if dep_raw.isdigit():
            try:
                dept = Department.objects.get(pk=int(dep_raw))
                indent.department = dept
                update_fields.append("department_id")
            except Department.DoesNotExist:
                messages.warning(
                    request,
                    f"Department ID '{dep_raw}' not found — assignment skipped.",
                    extra_tags="toast",
                )
        elif dep_raw:
            try:
                indent.department = Department.objects.get(name=dep_raw)
                update_fields.append("department_id")
            except Department.DoesNotExist:
                messages.warning(
                    request,
                    f"Department '{dep_raw}' not found — assignment skipped.",
                    extra_tags="toast",
                )

        # Date required
        date_raw = request.POST.get("date_required", "").strip()
        if date_raw:
            try:
                indent.date_required = date_type.fromisoformat(date_raw)
                update_fields.append("date_required")
            except (ValueError, TypeError):
                pass
        else:
            indent.date_required = None
            update_fields.append("date_required")

        # Notes
        indent.notes = request.POST.get("notes", "")
        update_fields.append("notes")

        indent.save(update_fields=list(set(update_fields)))

        is_partial = request.POST.get("partial") == "1"
        if is_partial:
            from django.http import JsonResponse

            return JsonResponse(
                {
                    "ok": True,
                    "toast_message": f"Indent {indent.mrn} updated.",
                    "reload": {
                        "url": reverse("indents_table"),
                        "target": "#indents_table",
                    },
                }
            )
        messages.success(request, f"Indent {indent.mrn} updated.", extra_tags="toast")
        return redirect("indent_detail", pk=pk)


@require_POST
@csrf_protect
def indent_update_status(request, pk: int, status: str):
    indent = get_object_or_404(Indent, pk=pk)
    target = (status or "").upper()
    current = (indent.status or "").upper() or "SUBMITTED"
    allowed = {
        "SUBMITTED": {"APPROVED"},
        "APPROVED": {"PROCESSING"},
        "PROCESSING": {"COMPLETED", "CANCELLED"},
    }
    # Permission: approval restricted to staff/superuser or explicit permission
    if target == "APPROVED":
        user = getattr(request, "user", None)
        if not (
            getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
            or user.has_perm("inventory.change_indent")
        ):
            from django.http import HttpResponse

            return HttpResponse("Forbidden", status=403)
    # Validate transition
    if current not in allowed or target not in allowed[current]:
        from django.http import HttpResponse

        return HttpResponse("Invalid status transition", status=400)
    # Apply transition and audit fields where applicable
    indent.status = target
    if target in {"APPROVED", "COMPLETED"}:
        try:
            indent.processed_by = getattr(request, "user", None)
        except Exception:
            indent.processed_by = None
        indent.date_processed = timezone.now()
    indent.save(
        update_fields=["status", "processed_by", "date_processed", "updated_at"]
    ) if target in {"APPROVED", "COMPLETED"} else indent.save(
        update_fields=["status", "updated_at"]
    )  # type: ignore
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


@require_POST
@csrf_protect
def indents_consolidate(request):
    """Consolidate selected approved indents into POs by supplier.

    Expects POST with one or more `indent_id` values or `ids` CSV.
    Returns partial updated table if HTMX, else redirects to orders list.
    """
    ids: list[int] = []
    if request.POST.getlist("indent_id"):
        try:
            ids = [
                int(x) for x in request.POST.getlist("indent_id") if str(x).isdigit()
            ]
        except Exception:
            ids = []
    elif request.POST.get("ids"):
        try:
            ids = [
                int(x.strip())
                for x in request.POST.get("ids", "").split(",")
                if x.strip().isdigit()
            ]
        except Exception:
            ids = []
    result = indent_consolidation_service.consolidate_approved_indents(ids)
    # For HTMX, return refreshed table
    if request.headers.get("HX-Request"):
        view = IndentsTableView()
        view.request = request
        ctx = view.get_context_data()
        ctx["consolidation"] = result
        return render(request, view.template_name, ctx)
    # Non-HTMX: go to orders list to review created POs
    return redirect("purchase_orders_list")


def consolidate_indents(request):
    """Preview consolidation of APPROVED indents grouped by preferred supplier.

    GET: shows grouped suppliers and summed pending quantities (requested - issued).
    Optional query param `ids` as CSV of indent IDs to constrain the scope.
    POST: performs consolidation via service and redirects with a success message.
    """
    ids: list[int] = []
    if request.GET.get("ids"):
        try:
            ids = [
                int(x.strip())
                for x in request.GET.get("ids", "").split(",")
                if x.strip().isdigit()
            ]
        except Exception:
            ids = []
    base_filter = {"indent__status": "APPROVED"}
    if ids:
        base_filter["indent_id__in"] = ids
    # Gather approved indent items with pending quantities and a preferred supplier
    qs = IndentItemModel.objects.select_related(
        "item", "indent", "item__preferred_supplier", "item__unit"
    ).filter(**base_filter)
    groups: dict[int, dict] = {}
    total_items = 0
    for ii in qs:
        req = (ii.requested_qty or 0) or 0
        iss = (ii.issued_qty or 0) or 0
        pending = req - iss
        if pending <= 0:
            continue
        item = ii.item  # type: ignore
        supplier_id = getattr(item, "preferred_supplier_id", None)
        if not supplier_id:
            continue
        g = groups.setdefault(supplier_id, {"items": {}, "supplier": None})
        if g["supplier"] is None:
            try:
                g["supplier"] = SupplierModel.objects.only("supplier_id", "name").get(
                    pk=supplier_id
                )
            except Exception:
                g["supplier"] = None
        # Build unit display from the related unit FK
        try:
            unit_display = (
                (item.unit.purchase_unit or str(item.unit)) if item.unit_id else ""
            )
        except Exception:
            unit_display = ""
        entry = g["items"].setdefault(
            item.pk,
            {"item": item, "qty": 0, "unit_display": unit_display, "mrn_lines": []},
        )
        entry["qty"] += pending
        # Track which MRN contributed and how much (Fix 5)
        mrn_label = getattr(ii.indent, "mrn", None) or f"Indent {ii.indent_id}"
        entry["mrn_lines"].append({"mrn": mrn_label, "qty": pending})
        total_items += 1
    # Transform to template-friendly structure
    grouped = []
    for supplier_id, data in groups.items():
        items_list = sorted(
            data["items"].values(), key=lambda x: getattr(x["item"], "name", "")
        )
        grouped.append(
            {
                "supplier": data["supplier"],
                "supplier_id": supplier_id,
                "items": items_list,
                "total_lines": len(items_list),
            }
        )
    # Sort suppliers by name
    grouped.sort(key=lambda g: (getattr(g["supplier"], "name", "") or "").lower())

    if request.method == "POST":
        # Read per-item qty overrides and exclusions from POST data (Fixes 3+4)
        from decimal import Decimal as _Decimal

        qty_overrides: dict[int, _Decimal] = {}
        excluded_item_ids: set[int] = set()
        # Collect all known item IDs from the consolidated groups to check exclusions
        all_item_ids: set[int] = set()
        for grp in grouped:
            for row in grp["items"]:
                iid = row["item"].pk
                all_item_ids.add(iid)
                # Checkbox: present in POST means included, absent means excluded
                if f"include_item_{iid}" not in request.POST:
                    excluded_item_ids.add(iid)
                # Qty override
                raw = request.POST.get(f"qty_override_{iid}", "")
                if raw:
                    try:
                        val = _Decimal(str(raw))
                        if val > 0:
                            qty_overrides[iid] = val
                    except Exception:
                        pass
        # If no specific IDs were requested, resolve all currently-approved indent IDs
        consolidate_ids = ids
        if not consolidate_ids:
            from ..models import Indent as _Indent

            consolidate_ids = list(
                _Indent.objects.filter(status="APPROVED").values_list(
                    "indent_id", flat=True
                )
            )
        result = indent_consolidation_service.consolidate_approved_indents(
            consolidate_ids,
            qty_overrides=qty_overrides,
            excluded_item_ids=excluded_item_ids,
        )
        if result.created_po_ids:
            messages.success(
                request,
                f"Created {len(result.created_po_ids)} purchase order(s)",
                extra_tags="toast",
            )
            return redirect("purchase_orders_list")
        messages.info(
            request, "No eligible items found to consolidate", extra_tags="toast"
        )
        return redirect("indents_list")

    total_supplier_count = len(grouped)
    total_item_count = sum(grp["total_lines"] for grp in grouped)
    return render(
        request,
        "inventory/indents_consolidate_preview.html",
        {
            "groups": grouped,
            "total_groups": len(grouped),
            "total_items": total_items,
            "total_supplier_count": total_supplier_count,
            "total_item_count": total_item_count,
            "ids_csv": ",".join(str(x) for x in ids) if ids else "",
        },
    )


def issue_indent(request, pk: int):
    indent = get_object_or_404(Indent, pk=pk)
    items = list(
        indent.indentitem_set.select_related("item").order_by("indent_item_id").all()
    )
    # Build formset for all items in this indent
    if request.method == "POST":
        Formset = forms.formset_factory(
            IndentItemIssueForm, formset=IndentIssueFormset, extra=0
        )  # type: ignore
        formset = Formset(request.POST)
        if formset.is_valid():
            lines: list[indent_issue_service.IssueLine] = []
            for form in formset.forms:
                data = form.cleaned_data
                lines.append(
                    indent_issue_service.IssueLine(
                        indent_item_id=int(data.get("indent_item_id")),
                        issue_qty=data.get("issue_qty"),
                        source_location=(data.get("source_location") or ""),
                    )
                )
            result = indent_issue_service.issue_indent(
                indent.indent_id, lines, request.user
            )
            if result.ok:
                messages.success(request, result.message, extra_tags="toast")
                return redirect("indent_detail", pk=indent.pk)
            messages.info(request, result.message, extra_tags="toast")
            return redirect("indent_detail", pk=indent.pk)
    else:
        Formset = forms.formset_factory(
            IndentItemIssueForm, formset=IndentIssueFormset, extra=0
        )  # type: ignore
        initial = IndentIssueFormset.initial_for_indent(indent.indent_id)
        formset = Formset(initial=initial)

    # Pair items with forms for template rendering
    pairs = list(zip(items, formset.forms))
    return render(
        request,
        "inventory/indent_issue_form.html",
        {
            "indent": indent,
            "items": items,
            "formset": formset,
            "pairs": pairs,
        },
    )


def generate_low_stock_indent(request):
    """D5: One-click indent for all items below their reorder point."""
    low_stock_items = list(
        Item.objects.filter(
            is_active=True,
            reorder_point__isnull=False,
            current_stock__isnull=False,
            current_stock__lt=F("reorder_point"),
        )
        .filter(reorder_point__gt=0)
        .select_related("unit")
        .order_by("name")
        .only(
            "item_id",
            "name",
            "unit_id",
            "current_stock",
            "reorder_point",
            "minimum_order_qty",
        )
    )

    enriched_items = []
    for item in low_stock_items:
        reorder_pt = float(item.reorder_point or 0)
        current = float(item.current_stock or 0)
        min_order = float(item.minimum_order_qty or 0)
        suggested = max(reorder_pt - current, min_order)
        enriched_items.append(
            {
                "item": item,
                "current_stock": current,
                "reorder_point": reorder_pt,
                "minimum_order_qty": min_order,
                "suggested_qty": round(suggested, 2),
            }
        )

    if request.method == "POST":
        if not enriched_items:
            messages.warning(request, "No low-stock items found.", extra_tags="toast")
            return redirect("items_list")

        ts = timezone.now().strftime("%Y%m%d%H%M%S")
        mrn = f"LSI-{ts}-{uuid.uuid4().hex[:6].upper()}"
        with transaction.atomic():
            indent = Indent.objects.create(
                mrn=mrn,
                requested_by=getattr(request.user, "username", "") or "",
                status="PENDING",
                notes="Auto-generated from low-stock alert",
            )
            for entry in enriched_items:
                IndentItemModel.objects.create(
                    indent=indent,
                    item=entry["item"],
                    requested_qty=entry["suggested_qty"],
                )
        messages.success(
            request,
            f"Indent {mrn} created with {len(enriched_items)} item(s).",
            extra_tags="toast",
        )
        return redirect("indent_detail", pk=indent.pk)

    return render(
        request,
        "inventory/low_stock_indent_confirm.html",
        {"enriched_items": enriched_items},
    )
