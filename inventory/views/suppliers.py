import csv
import io
import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from ..models import Supplier
from ..forms import SupplierForm, BulkUploadForm, BulkDeleteForm
from ..services import supplier_service

logger = logging.getLogger(__name__)


class SuppliersListView(TemplateView):
    template_name = "inventory/suppliers_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = (self.request.GET.get("q") or "").strip()
        show_inactive = (self.request.GET.get("show_inactive") or "").strip()
        ctx.update({"q": q, "show_inactive": show_inactive})
        return ctx


class SuppliersTableView(TemplateView):
    template_name = "inventory/_suppliers_table.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = (self.request.GET.get("q") or "").strip()
        show_inactive = (self.request.GET.get("show_inactive") or "").strip()
        qs = Supplier.objects.all()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(contact_person__icontains=q)
                | Q(email__icontains=q)
            )
        if not show_inactive:
            qs = qs.filter(is_active=True)
        qs = qs.order_by("name")
        paginator = Paginator(qs, 25)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        ctx.update({"page_obj": page_obj, "q": q, "show_inactive": show_inactive})
        return ctx


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


class SupplierToggleActiveView(View):
    def get(self, request, pk: int):
        supplier = get_object_or_404(Supplier, pk=pk)
        if supplier.is_active:
            supplier_service.deactivate_supplier(supplier.pk)
        else:
            supplier_service.reactivate_supplier(supplier.pk)
        view = SuppliersTableView.as_view()
        return view(request)


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
