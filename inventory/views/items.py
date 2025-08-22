import csv
import io
import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import DatabaseError, IntegrityError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from ..models import Item, StockTransaction
from ..forms import ItemForm, BulkUploadForm
from ..services import item_service

logger = logging.getLogger(__name__)

EXCLUDED_FIELDS = ["name", "base_unit", "purchase_unit", "category"]


class ItemsListView(TemplateView):
    template_name = "inventory/items_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request
        q = (request.GET.get("q") or "").strip()
        category = (request.GET.get("category") or "").strip()
        subcategory = (request.GET.get("subcategory") or "").strip()
        active = (request.GET.get("active") or "").strip()
        page_size = (request.GET.get("page_size") or "25").strip()
        sort = (request.GET.get("sort") or "name").strip()
        direction = (request.GET.get("direction") or "asc").strip()
        categories = (
            Item.objects.exclude(category__isnull=True)
            .exclude(category="")
            .order_by("category")
            .values_list("category", flat=True)
            .distinct()
        )
        subcategories = (
            Item.objects.exclude(sub_category__isnull=True)
            .exclude(sub_category="")
            .order_by("sub_category")
            .values_list("sub_category", flat=True)
            .distinct()
        )
        ctx.update(
            {
                "q": q,
                "category": category,
                "subcategory": subcategory,
                "active": active,
                "page_size": page_size,
                "sort": sort,
                "direction": direction,
                "categories": categories,
                "subcategories": subcategories,
            }
        )
        return ctx


class ItemsTableView(TemplateView):
    template_name = "inventory/_items_table.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request
        q = (request.GET.get("q") or "").strip()
        category = (request.GET.get("category") or "").strip()
        subcategory = (request.GET.get("subcategory") or "").strip()
        active = (request.GET.get("active") or "").strip()
        sort = (request.GET.get("sort") or "name").strip()
        direction = (request.GET.get("direction") or "asc").strip()
        page_size = request.GET.get("page_size") or 25
        qs = Item.objects.all()
        if q:
            qs = qs.filter(name__icontains=q)
        if category:
            qs = qs.filter(category=category)
        if subcategory:
            qs = qs.filter(sub_category=subcategory)
        if active:
            if active == "1":
                qs = qs.filter(is_active=True)
            elif active == "0":
                qs = qs.filter(is_active=False)
        allowed_sorts = {
            "item_id",
            "name",
            "base_unit",
            "category",
            "sub_category",
            "current_stock",
            "reorder_point",
            "is_active",
        }
        if sort not in allowed_sorts:
            sort = "name"
        ordering = sort if direction != "desc" else f"-{sort}"
        qs = qs.order_by(ordering)
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
                "category": category,
                "subcategory": subcategory,
                "active": active,
                "page_size": per_page,
                "sort": sort,
                "direction": direction,
            }
        )
        return ctx


class ItemsExportView(View):
    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        category = (request.GET.get("category") or "").strip()
        subcategory = (request.GET.get("subcategory") or "").strip()
        active = (request.GET.get("active") or "").strip()
        sort = (request.GET.get("sort") or "name").strip()
        direction = (request.GET.get("direction") or "asc").strip()
        qs = Item.objects.all()
        if q:
            qs = qs.filter(name__icontains=q)
        if category:
            qs = qs.filter(category=category)
        if subcategory:
            qs = qs.filter(sub_category=subcategory)
        if active:
            if active == "1":
                qs = qs.filter(is_active=True)
            elif active == "0":
                qs = qs.filter(is_active=False)
        allowed_sorts = {
            "item_id",
            "name",
            "base_unit",
            "category",
            "sub_category",
            "current_stock",
            "reorder_point",
            "is_active",
        }
        if sort not in allowed_sorts:
            sort = "name"
        ordering = sort if direction != "desc" else f"-{sort}"
        qs = qs.order_by(ordering)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=items.csv"
        writer = csv.writer(response)
        writer.writerow(
            [
                "ID",
                "Name",
                "Base Unit",
                "Category",
                "Subcategory",
                "Current Stock",
                "Reorder Point",
                "Active",
            ]
        )
        for item in qs:
            writer.writerow(
                [
                    item.item_id,
                    item.name,
                    item.base_unit,
                    item.category,
                    item.sub_category,
                    item.current_stock,
                    item.reorder_point,
                    item.is_active,
                ]
            )
        return response


class ItemCreateView(View):
    template_name = "inventory/item_form.html"

    def get(self, request):
        suggest_url = reverse("item_suggest")
        form = ItemForm(suggest_url=suggest_url)
        ctx = {"form": form, "is_edit": False, "excluded_fields": EXCLUDED_FIELDS}
        return render(request, self.template_name, ctx)

    def post(self, request):
        suggest_url = reverse("item_suggest")
        form = ItemForm(request.POST, suggest_url=suggest_url)
        if form.is_valid():
            form.save()
            messages.success(request, "Item created")
            return redirect("items_list")
        ctx = {"form": form, "is_edit": False, "excluded_fields": EXCLUDED_FIELDS}
        return render(request, self.template_name, ctx)


class ItemEditView(View):
    template_name = "inventory/item_form.html"

    def get_object(self, pk: int):
        try:
            return get_object_or_404(Item, pk=pk)
        except (DatabaseError, ValueError):  # pragma: no cover - defensive
            logger.exception("Error retrieving item %s", pk)
            raise Http404("Item not found")

    def get(self, request, pk: int):
        item = self.get_object(pk)
        try:
            suggest_url = reverse("item_suggest")
            form = ItemForm(instance=item, suggest_url=suggest_url)
        except (DatabaseError, ValueError):
            logger.exception("Error loading form for item %s", pk)
            messages.error(request, "Unable to load item")
            return redirect("items_list")
        ctx = {
            "form": form,
            "is_edit": True,
            "item": item,
            "excluded_fields": EXCLUDED_FIELDS,
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk: int):
        item = self.get_object(pk)
        try:
            suggest_url = reverse("item_suggest")
            form = ItemForm(request.POST, instance=item, suggest_url=suggest_url)
        except (DatabaseError, ValueError):
            logger.exception("Error loading form for item %s", pk)
            messages.error(request, "Unable to load item")
            return redirect("items_list")
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Item updated")
                return redirect("items_list")
            except (ValidationError, DatabaseError):
                messages.error(request, "Unable to save item")
        ctx = {
            "form": form,
            "is_edit": True,
            "item": item,
            "excluded_fields": EXCLUDED_FIELDS,
        }
        return render(request, self.template_name, ctx)


class ItemDetailView(View):
    template_name = "inventory/item_detail.html"

    def get(self, request, pk: int):
        try:
            details = item_service.get_item_details(pk)
        except (DatabaseError, ValueError):  # pragma: no cover - defensive
            logger.exception("Error retrieving item %s", pk)
            raise Http404("Item not found")
        if not details:
            raise Http404("Item not found")
        return render(request, self.template_name, {"item": details})


class ItemDeleteView(View):
    template_name = "inventory/item_confirm_delete.html"

    def get_object(self, pk: int):
        try:
            return get_object_or_404(Item, pk=pk)
        except (DatabaseError, ValueError):  # pragma: no cover - defensive
            logger.exception("Error retrieving item %s", pk)
            raise Http404("Item not found")

    def get(self, request, pk: int):
        item = self.get_object(pk)
        return render(request, self.template_name, {"item": item})

    def post(self, request, pk: int):
        item = self.get_object(pk)
        if StockTransaction.objects.filter(item=item).exists():
            ok, _ = item_service.deactivate_item(item.pk)
            if ok:
                messages.success(request, "Item deactivated")
            else:  # pragma: no cover - defensive
                messages.error(request, "Unable to delete item")
            return redirect("items_list")
        try:
            item.delete()
            item_service.get_all_items_with_stock.clear()
            item_service.get_distinct_departments_from_items.clear()
            messages.success(request, "Item deleted")
        except IntegrityError:
            ok, _ = item_service.deactivate_item(item.pk)
            if ok:
                messages.success(request, "Item deactivated")
            else:  # pragma: no cover - defensive
                messages.error(request, "Unable to delete item")
        except DatabaseError:  # pragma: no cover - defensive
            logger.exception("Error deleting item %s", pk)
            messages.error(request, "Unable to delete item")
        return redirect("items_list")


class ItemSuggestView(TemplateView):
    template_name = "inventory/_item_suggest_fields.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        name = (self.request.GET.get("name") or "").strip()
        base, purchase, category = item_service.suggest_category_and_units(name)
        ctx.update(
            {"base": base or "", "purchase": purchase or "", "category": category or ""}
        )
        return ctx


class ItemsBulkUploadView(View):
    template_name = "inventory/bulk_upload.html"

    def get(self, request):
        form = BulkUploadForm()
        ctx = {
            "form": form,
            "inserted": 0,
            "errors": [],
            "title": "Bulk Upload Items",
            "back_url": "items_list",
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
                form_row = ItemForm(row)
                if form_row.is_valid():
                    form_row.save()
                    inserted += 1
                else:
                    errors.append(str(form_row.errors))
        ctx = {
            "form": form,
            "inserted": inserted,
            "errors": errors,
            "title": "Bulk Upload Items",
            "back_url": "items_list",
        }
        return render(request, self.template_name, ctx)
