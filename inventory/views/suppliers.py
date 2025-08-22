import csv
import io
import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from ..models import Supplier
from ..forms import SupplierForm, BulkUploadForm, BulkDeleteForm
from ..services import supplier_service

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
        ctx.update(
            {
                "q": q,
                "active": active,
                "page_size": page_size,
                "sort": sort,
                "direction": direction,
            }
        )
        return ctx


class SuppliersTableView(TemplateView):
    template_name = "inventory/_suppliers_table.html"

    def get_queryset(self):
        request = self.request
        q = (request.GET.get("q") or "").strip()
        active = (request.GET.get("active") or "").strip()
        sort = (request.GET.get("sort") or "name").strip()
        direction = (request.GET.get("direction") or "asc").strip()
        qs = Supplier.objects.all()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(contact_person__icontains=q)
                | Q(email__icontains=q)
            )
        if active:
            if active == "1":
                qs = qs.filter(is_active=True)
            elif active == "0":
                qs = qs.filter(is_active=False)
        allowed_sorts = {"supplier_id", "name", "contact_person", "email", "phone", "is_active"}
        if sort not in allowed_sorts:
            sort = "name"
        ordering = sort if direction != "desc" else f"-{sort}"
        return qs.order_by(ordering)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request
        q = (request.GET.get("q") or "").strip()
        active = (request.GET.get("active") or "").strip()
        sort = (request.GET.get("sort") or "name").strip()
        direction = (request.GET.get("direction") or "asc").strip()
        page_size = request.GET.get("page_size") or 25
        qs = self.get_queryset()
        try:
            per_page = int(page_size)
        except (TypeError, ValueError):
            per_page = 25
        paginator = Paginator(qs, per_page)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        ctx.update(
            {
                "page_obj": page_obj,
                "q": q,
                "active": active,
                "sort": sort,
                "direction": direction,
                "page_size": per_page,
            }
        )
        return ctx

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "1":
            qs = self.get_queryset()
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = "attachment; filename=suppliers.csv"
            writer = csv.writer(response)
            writer.writerow(["ID", "Name", "Contact", "Email", "Phone", "Active"])
            for sup in qs:
                writer.writerow(
                    [
                        sup.supplier_id,
                        sup.name,
                        sup.contact_person,
                        sup.email,
                        sup.phone,
                        sup.is_active,
                    ]
                )
            return response
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
