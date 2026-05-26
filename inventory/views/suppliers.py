import csv
import io
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.generic import DetailView, TemplateView

from ..forms.bulk_forms import BulkDeleteForm, BulkUploadForm
from ..forms.supplier_forms import SupplierForm
from ..models import PurchaseOrder, Supplier
from ..services import list_utils, supplier_service
from ..services.exceptions import SupplierServiceError

logger = logging.getLogger(__name__)


class SuppliersListView(TemplateView):
    """Display supplier list filters and counts.

    GET params:
        q, active, page_size, sort, direction control filtering and
        ordering. Template: inventory/suppliers_list.html.
    """

    template_name = "inventory/suppliers_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = (self.request.GET.get("q") or "").strip()
        active = (self.request.GET.get("active") or "").strip()
        page_size = (self.request.GET.get("page_size") or "25").strip()
        sort = (self.request.GET.get("sort") or "name").strip()
        direction = (self.request.GET.get("direction") or "asc").strip()
        view = (self.request.GET.get("view") or "table").strip()
        total_suppliers = Supplier.objects.count()
        filters = [
            {
                "name": "active",
                "label": "Status",
                "value": active,
                "list_id": "active-statuses",
                "options": [
                    {"value": "", "label": "All"},
                    {"value": "1", "label": "Active"},
                    {"value": "0", "label": "Inactive"},
                ],
            }
        ]
        hx_view_name = "suppliers_cards" if view == "cards" else "suppliers_table"
        container_id = "suppliers_cards" if view == "cards" else "suppliers_table"

        export_params = self.request.GET.copy()
        export_params.pop("page", None)
        export_params["export"] = "1"
        export_href = f"{reverse('suppliers_table')}?{export_params.urlencode()}"

        toggle_table = self.request.GET.copy()
        toggle_table["view"] = "table"
        view_toggle_table_href = "?" + toggle_table.urlencode()
        toggle_cards = self.request.GET.copy()
        toggle_cards["view"] = "cards"
        view_toggle_cards_href = "?" + toggle_cards.urlencode()

        ctx.update(
            {
                "q": q,
                "active": active,
                "page_size": page_size,
                "sort": sort,
                "direction": direction,
                "view": view,
                "total_suppliers": total_suppliers,
                "filters": filters,
                "export_url": reverse("suppliers_table"),
                "export_href": export_href,
                "view_toggle_table_href": view_toggle_table_href,
                "view_toggle_cards_href": view_toggle_cards_href,
                "view_toggle_current": view,
                "page_size_options": [10, 25, 50, 100],
                "hx_view_name": hx_view_name,
                "container_id": container_id,
                "list_url": reverse("root"),
                "list_title": "Dashboard",
                "current_title": "Suppliers",
            }
        )
        # Include forms for inline creation and bulk upload
        if self.request.method == "POST":
            ctx["form"] = SupplierForm(self.request.POST)
            ctx["bulk_form"] = BulkUploadForm(self.request.POST, self.request.FILES)
        else:
            ctx["form"] = SupplierForm()
            ctx["bulk_form"] = BulkUploadForm()
        return ctx

    def post(self, request, *args, **kwargs):
        """Handle inline supplier creation and CSV bulk upload."""
        if request.POST.get("bulk_upload"):
            bulk_form = BulkUploadForm(request.POST, request.FILES)
            if bulk_form.is_valid():
                inserted = 0
                file = bulk_form.cleaned_data["file"]
                raw = file.read()
                for encoding in ("utf-8-sig", "utf-8", "latin-1"):
                    try:
                        raw = raw.decode(encoding)
                        break
                    except (UnicodeDecodeError, AttributeError):
                        continue
                else:
                    messages.error(
                        request,
                        "Could not decode CSV file — please save it as UTF-8.",
                        extra_tags="toast",
                    )
                    raw = ""
                data = io.StringIO(raw)
                reader = csv.DictReader(data)
                for row in reader:
                    form_row = SupplierForm(row)
                    if form_row.is_valid():
                        try:
                            supplier_service.add_supplier(form_row.cleaned_data)
                            inserted += 1
                        except SupplierServiceError as exc:
                            messages.error(request, str(exc), extra_tags="toast")
                    else:
                        messages.error(
                            request, str(form_row.errors), extra_tags="toast"
                        )
                messages.success(
                    request,
                    f"{inserted} supplier(s) uploaded successfully.",
                    extra_tags="toast",
                )
            else:
                messages.error(
                    request, "Please upload a valid CSV file.", extra_tags="toast"
                )
            return redirect("suppliers_list")

        form = SupplierForm(request.POST)
        if form.is_valid():
            try:
                supplier_service.add_supplier(form.cleaned_data)
                messages.success(
                    request,
                    f'Supplier "{form.cleaned_data.get("name")}" created successfully!',
                    extra_tags="toast",
                )
                return redirect("suppliers_list")
            except SupplierServiceError as exc:
                messages.error(request, str(exc), extra_tags="toast")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}", extra_tags="toast")
        return self.get(request, *args, **kwargs)


def _annotate_open_po_count(qs):
    """Annotate suppliers with count of open (non-received) purchase orders."""
    return qs.annotate(
        open_po_count=Count(
            "purchaseorder",
            filter=Q(purchaseorder__status__in=["DRAFT", "SENT"]),
        )
    )


class SuppliersTableView(TemplateView):
    """Render the paginated table of suppliers or export as CSV.

    GET params:
        q, active, sort, direction, page. `export=1` returns a CSV
        file. Template: inventory/_suppliers_table.html.
    """

    template_name = "inventory/_suppliers_table.html"

    def _get_queryset(self):
        qs = Supplier.objects.all()
        filters = {"active": "is_active"}
        allowed_sorts = {
            "supplier_id",
            "name",
            "contact_person",
            "email",
            "phone",
            "is_active",
        }
        qs, params = list_utils.apply_filters_sort(
            self.request,
            qs,
            search_fields=["name", "contact_person", "email"],
            filter_fields=filters,
            allowed_sorts=allowed_sorts,
            default_sort="name",
        )
        qs = _annotate_open_po_count(qs)
        self._filter_params = params
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self._get_queryset()
        page_obj, per_page = list_utils.paginate(self.request, qs)
        ctx.update(self._filter_params)
        ctx.update(
            {
                "page_obj": page_obj,
                "page_size": per_page,
                "container_id": "suppliers_table",
            }
        )
        return ctx

    def get(self, request, *args, **kwargs):
        qs = self._get_queryset()
        if request.GET.get("export") == "1":
            headers = ["ID", "Name", "Contact", "Email", "Phone", "Active"]

            def row(sup: Supplier):
                return [
                    sup.supplier_id,
                    sup.name,
                    sup.contact_person,
                    sup.email,
                    sup.phone,
                    sup.is_active,
                ]

            return list_utils.export_as_csv(qs, headers, row, "suppliers.csv")
        return super().get(request, *args, **kwargs)


class SuppliersCardView(TemplateView):
    """Render the paginated card grid of suppliers."""

    template_name = "inventory/suppliers_card.html"

    def _get_queryset(self):
        qs = Supplier.objects.all()
        filters = {"active": "is_active"}
        allowed_sorts = {
            "supplier_id",
            "name",
            "contact_person",
            "email",
            "phone",
            "is_active",
        }
        qs, params = list_utils.apply_filters_sort(
            self.request,
            qs,
            search_fields=["name", "contact_person", "email"],
            filter_fields=filters,
            allowed_sorts=allowed_sorts,
            default_sort="name",
        )
        qs = _annotate_open_po_count(qs)
        self._filter_params = params
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self._get_queryset()
        page_obj, per_page = list_utils.paginate(self.request, qs)
        ctx.update(self._filter_params)
        ctx.update({"page_obj": page_obj, "page_size": per_page, "view": "cards"})
        return ctx


class SupplierCreateView(View):
    """Create a new supplier; returns drawer partials and JSON."""

    template_name = "inventory/_supplier_form_partial.html"

    def get(self, request):
        form = SupplierForm()
        return render(request, self.template_name, {"form": form, "is_edit": False})

    def post(self, request):
        form = SupplierForm(request.POST)
        if form.is_valid():
            try:
                supplier = supplier_service.add_supplier(form.cleaned_data)
                return JsonResponse(
                    {"ok": True, "id": supplier.pk, "message": "Supplier created"}
                )
            except SupplierServiceError as exc:
                return JsonResponse({"ok": False, "message": str(exc)}, status=400)
        return render(
            request,
            self.template_name,
            {"form": form, "is_edit": False},
            status=400,
        )


class SupplierEditView(View):
    """Edit an existing supplier; returns drawer partials and JSON."""

    template_name = "inventory/_supplier_form_partial.html"

    def get(self, request, pk: int):
        supplier = get_object_or_404(Supplier, pk=pk)
        form = SupplierForm(instance=supplier)
        ctx = {"form": form, "is_edit": True, "supplier": supplier}
        return render(request, self.template_name, ctx)

    def post(self, request, pk: int):
        supplier = get_object_or_404(Supplier, pk=pk)
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            success, msg = supplier_service.update_supplier(
                supplier.pk, form.cleaned_data
            )
            if success:
                return JsonResponse({"ok": True, "message": "Supplier updated"})
            return JsonResponse({"ok": False, "message": msg}, status=400)
        ctx = {"form": form, "is_edit": True, "supplier": supplier}
        return render(request, self.template_name, ctx, status=400)


@method_decorator(csrf_protect, name="dispatch")
class SupplierToggleActiveView(View):
    """Toggle a supplier's active flag and return updated table.

    Accepts GET or POST and delegates to SuppliersTableView.
    """

    def _toggle(self, request, pk: int):
        supplier = get_object_or_404(Supplier, pk=pk)
        if supplier.is_active:
            supplier_service.deactivate_supplier(supplier.pk)
        else:
            supplier_service.reactivate_supplier(supplier.pk)
        if request.method == "POST":
            params = request.POST.copy()
            params.pop("csrfmiddlewaretoken", None)
            request.GET = params
            request.method = "GET"
        view_name = request.GET.get("view")
        view = (
            SuppliersCardView.as_view()
            if view_name == "cards"
            else SuppliersTableView.as_view()
        )
        return view(request)

    def post(self, request, pk: int):
        return self._toggle(request, pk)

    def get(self, request, pk: int):
        return self._toggle(request, pk)


class SuppliersBulkUploadView(View):
    """Bulk create suppliers from an uploaded CSV file.

    GET shows the upload form; POST processes the file and reports
    inserted rows and errors. Template: inventory/bulk_upload.html.
    """

    template_name = "inventory/bulk_upload.html"

    def get(self, request):
        form = BulkUploadForm()
        ctx = {
            "form": form,
            "inserted": 0,
            "errors": [],
            "title": "Bulk Upload Suppliers",
            "back_url": "suppliers_list",
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        inserted = 0
        errors: list[str] = []
        form = BulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]
            data = io.StringIO(file.read().decode("utf-8"))
            reader = csv.DictReader(data)
            for row in reader:
                form_row = SupplierForm(row)
                if form_row.is_valid():
                    try:
                        supplier_service.add_supplier(form_row.cleaned_data)
                        inserted += 1
                    except SupplierServiceError as exc:
                        errors.append(str(exc))
                else:
                    errors.append(str(form_row.errors))
        ctx = {
            "form": form,
            "inserted": inserted,
            "errors": errors,
            "title": "Bulk Upload Suppliers",
            "back_url": "suppliers_list",
        }
        return render(request, self.template_name, ctx)


class SuppliersBulkDeleteView(View):
    """Deactivate suppliers using a CSV list of names.

    GET shows the upload form; POST processes deletions.
    Template: inventory/bulk_delete.html.
    """

    template_name = "inventory/bulk_delete.html"

    def get(self, request):
        form = BulkDeleteForm()
        ctx = {
            "form": form,
            "deleted": 0,
            "errors": [],
            "title": "Bulk Delete Suppliers",
            "back_url": "suppliers_list",
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        deleted = 0
        errors: list[str] = []
        form = BulkDeleteForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]
            data = io.StringIO(file.read().decode("utf-8"))
            reader = csv.DictReader(data)
            for row in reader:
                name = (row.get("name") or "").strip()
                if name:
                    supplier = Supplier.objects.filter(name=name).first()
                    if supplier:
                        ok, _ = supplier_service.deactivate_supplier(supplier.pk)
                        if ok:
                            deleted += 1
                        else:
                            errors.append(f"Supplier '{name}' not found")
                    else:
                        errors.append(f"Supplier '{name}' not found")
                else:
                    errors.append("Missing name")
        ctx = {
            "form": form,
            "deleted": deleted,
            "errors": errors,
            "title": "Bulk Delete Suppliers",
            "back_url": "suppliers_list",
        }
        return render(request, self.template_name, ctx)


class SupplierSearchView(TemplateView):
    """Return supplier ``<option>`` elements for autocomplete.

    GET param `q` or first `*supplier` value provides the search term.
    Template: inventory/_supplier_options.html.
    """

    template_name = "inventory/_supplier_options.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query = (self.request.GET.get("q") or "").strip()
        if not query:
            for key, val in self.request.GET.items():
                if key.endswith("supplier"):
                    query = val
                    break
        suppliers = Supplier.objects.filter(
            is_active=True, name__icontains=query
        ).order_by("name")[:20]
        ctx["suppliers"] = suppliers
        return ctx


class SuppliersBulkUploadPartialView(View):
    """Return the bulk upload drawer partial for Suppliers.

    Renders `inventory/_bulk_upload_partial.html` with the upload_url pointing
    to the suppliers list endpoint, so the form posts to the existing handler
    that supports `bulk_upload=1` and redirects/messages accordingly.
    """

    def get(self, request):
        form = BulkUploadForm()
        ctx = {
            "form": form,
            "upload_url": reverse("suppliers_list"),
            "title": "Bulk Upload Suppliers",
            "bulk_upload": 1,
            "help_text": "CSV must include headers compatible with the supplier form fields.",
        }
        return render(request, "inventory/_bulk_upload_partial.html", ctx)


class SupplierDetailView(LoginRequiredMixin, DetailView):
    """Read-only supplier detail — renders as drawer partial."""

    model = Supplier
    template_name = "inventory/_supplier_detail_partial.html"
    context_object_name = "supplier"

    def get(self, request, *args, **kwargs):
        supplier = get_object_or_404(Supplier, pk=kwargs["pk"])
        open_pos = PurchaseOrder.objects.filter(
            supplier=supplier,
            status__in=["DRAFT", "SENT"],
        ).count()
        return render(
            request,
            self.template_name,
            {"supplier": supplier, "open_po_count": open_pos},
        )


class SupplierDeleteView(LoginRequiredMixin, View):
    """Delete a supplier if it has no open POs; otherwise show an error."""

    def post(self, request, pk: int):
        supplier = get_object_or_404(Supplier, pk=pk)
        open_pos = PurchaseOrder.objects.filter(
            supplier=supplier,
            status__in=["DRAFT", "SENT"],
        ).count()
        if open_pos:
            messages.error(
                request,
                f"Cannot delete '{supplier.name}' — it has {open_pos} open purchase order(s). "
                "Deactivate instead or close the POs first.",
                extra_tags="toast",
            )
            return redirect("suppliers_list")
        name = supplier.name
        supplier.delete()
        messages.success(request, f"Supplier '{name}' deleted.", extra_tags="toast")
        return redirect("suppliers_list")
