import io
import logging

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from ..models import Supplier
from ..forms.supplier_forms import SupplierForm
from ..forms.bulk_forms import BulkUploadForm, BulkDeleteForm
from ..services import supplier_service, list_utils

logger = logging.getLogger(__name__)


class SuppliersListView(TemplateView):
    template_name = "inventory/suppliers_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = (self.request.GET.get("q") or "").strip()
        active = (self.request.GET.get("active") or "").strip()
        page_size = (self.request.GET.get("page_size") or "25").strip()
        sort = (self.request.GET.get("sort") or "name").strip()
        direction = (self.request.GET.get("direction") or "asc").strip()
        total_suppliers = Supplier.objects.count()
        ctx.update(
            {
                "q": q,
                "active": active,
                "page_size": page_size,
                "sort": sort,
                "direction": direction,
                "total_suppliers": total_suppliers,
            }
        )
        return ctx


class SuppliersTableView(TemplateView):
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
        self._filter_params = params
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self._get_queryset()
        page_obj, per_page = list_utils.paginate(self.request, qs)
        ctx.update(self._filter_params)
        ctx.update({"page_obj": page_obj, "page_size": per_page})
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


class SupplierCreateView(View):
    template_name = "inventory/supplier_form.html"

    def get(self, request):
        form = SupplierForm()
        return render(request, self.template_name, {"form": form, "is_edit": False})

    def post(self, request):
        form = SupplierForm(request.POST)
        if form.is_valid():
            success, msg = supplier_service.add_supplier(form.cleaned_data)
            if success:
                return redirect("suppliers_list")
            messages.error(request, msg)
        return render(request, self.template_name, {"form": form, "is_edit": False})


class SupplierEditView(View):
    template_name = "inventory/supplier_form.html"

    def get(self, request, pk: int):
        supplier = get_object_or_404(Supplier, pk=pk)
        form = SupplierForm(instance=supplier)
        ctx = {"form": form, "is_edit": True, "supplier": supplier}
        return render(request, self.template_name, ctx)

    def post(self, request, pk: int):
        supplier = get_object_or_404(Supplier, pk=pk)
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            success, msg = supplier_service.update_supplier(supplier.pk, form.cleaned_data)
            if success:
                return redirect("suppliers_list")
            messages.error(request, msg)
        ctx = {"form": form, "is_edit": True, "supplier": supplier}
        return render(request, self.template_name, ctx)


@method_decorator(csrf_protect, name="dispatch")
class SupplierToggleActiveView(View):
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
        view = SuppliersTableView.as_view()
        return view(request)

    def post(self, request, pk: int):
        return self._toggle(request, pk)

    def get(self, request, pk: int):
        return self._toggle(request, pk)


class SuppliersBulkUploadView(View):
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
                    success, msg = supplier_service.add_supplier(form_row.cleaned_data)
                    if success:
                        inserted += 1
                    else:
                        errors.append(msg)
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
    """Return supplier <option> elements matching a query."""

    template_name = "inventory/_supplier_options.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query = (self.request.GET.get("q") or "").strip()
        if not query:
            for key, val in self.request.GET.items():
                if key.endswith("supplier"):
                    query = val
                    break
        suppliers = Supplier.objects.filter(name__icontains=query)[:20]
        ctx["suppliers"] = suppliers
        return ctx
