import csv
import io
import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView
from django.urls import reverse

from ..models import Item, StockTransaction
from ..forms.item_forms import ItemForm
from ..forms.bulk_forms import BulkUploadForm
from ..services import item_service, list_utils
from ..services.supabase_categories import get_categories as get_supabase_categories

logger = logging.getLogger(__name__)

EXCLUDED_FIELDS = ["name", "base_unit", "purchase_unit"]


def _filter_and_sort_items(request, qs=None):
    """Return items queryset filtered and sorted according to request params."""
    qs = qs or Item.objects.all()
    filters = {
        "active": "is_active",
    }
    allowed_sorts = {
        "item_id",
        "name",
        "base_unit",
        "current_stock",
        "reorder_point",
        "is_active",
    }
    return list_utils.apply_filters_sort(
        request,
        qs,
        search_fields=["name"],
        filter_fields=filters,
        allowed_sorts=allowed_sorts,
        default_sort="name",
    )


class ItemsListView(TemplateView):
    """Show item filters and options for the list view.

    GET params:
        q, category, subcategory, active, page_size, sort, direction
        control filtering, pagination and ordering.
    Template: inventory/items_list.html.
    """

    template_name = "inventory/items_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        # Resolve category related data for the filter form
        category = (request.GET.get("category") or "").strip()
        subcategory = (request.GET.get("subcategory") or "").strip()

        categories_map: dict | None = None
        try:
            categories_map = get_supabase_categories()
        except Exception:  # pragma: no cover - defensive
            categories_map = {}
            logger.exception("Failed to load categories")
        categories = [c["name"] for c in categories_map.get(None, [])]
        subcategories: list[str] = []
        if category:
            subcategories = [c["name"] for c in categories_map.get(category, [])]

        # Build initial queryset and render the table fragment
        qs, params = _filter_and_sort_items(request)
        page_obj, per_page = list_utils.paginate(request, qs)
        table_ctx = {**params, "page_obj": page_obj, "page_size": per_page}
        items_table = render_to_string(
            "inventory/_items_table.html", table_ctx, request=request
        )

        ctx.update(params)
        filters = [
            {
                "name": "active",
                "value": params.get("active", ""),
                "list_id": "item-active",
                "id": "filter-active",
                "options": [
                    {"value": "", "label": "All"},
                    {"value": "1", "label": "Active"},
                    {"value": "0", "label": "Inactive"},
                ],
            },
            {
                "name": "category",
                "value": category,
                "list_id": "item-category",
                "id": "filter-category",
                "options": [{"value": "", "label": "All"}] + [{"value": c} for c in categories],
            },
            {
                "name": "subcategory",
                "value": subcategory,
                "list_id": "item-subcategory",
                "id": "filter-subcategory",
                "options": [{"value": "", "label": "All"}] + [{"value": sc} for sc in subcategories],
            },
        ]
        ctx.update(
            {
                "category": category,
                "subcategory": subcategory,
                "categories": categories,
                "subcategories": subcategories,
                "categories_map": categories_map,
                "page_size": per_page,
                "items_table": items_table,
                "filters": filters,
                "export_url": reverse("items_export"),
            }
        )
        return ctx


class ItemsTableView(TemplateView):
    """Render the paginated table of items.

    Accepts the same GET filters as ItemsListView plus a page number.
    Template: inventory/_items_table.html.
    """

    template_name = "inventory/_items_table.html"

    def _get_queryset(self):
        qs, params = _filter_and_sort_items(self.request)
        self._filter_params = params
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self._get_queryset()
        page_obj, per_page = list_utils.paginate(self.request, qs)
        ctx.update(self._filter_params)
        ctx.update({"page_obj": page_obj, "page_size": per_page})
        return ctx


class ItemsExportView(View):
    """Export the filtered item list as CSV.

    Uses the same GET parameters as ItemsListView for filtering.
    """

    def get(self, request):
        qs, _ = _filter_and_sort_items(request)
        headers = [
            "ID",
            "Name",
            "Base Unit",
            "Current Stock",
            "Reorder Point",
            "Active",
        ]

        def row(item: Item):
            return [
                item.item_id,
                item.name,
                item.base_unit,
                item.current_stock,
                item.reorder_point,
                item.is_active,
            ]

        return list_utils.export_as_csv(qs, headers, row, "items.csv")


class ItemCreateView(View):
    """Create a new item using ItemForm.

    GET renders an empty form; POST saves the item.
    Template: inventory/item_form.html.
    """

    template_name = "inventory/item_form.html"

    def get(self, request):
        form = ItemForm()
        ctx = {"form": form, "is_edit": False, "excluded_fields": EXCLUDED_FIELDS}
        return render(request, self.template_name, ctx)

    def post(self, request):
        form = ItemForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get("HX-Request"):
                items = Item.objects.order_by("name")[:20]
                options_html = render_to_string(
                    "inventory/_item_options.html", {"items": items}, request=request
                )
                toast_html = render_to_string(
                    "components/toast.html", {"message": "Item created"}, request=request
                )
                response = HttpResponse(
                    options_html
                    + f'<div id="toast-container" hx-swap-oob="beforeend">{toast_html}</div>'
                )
                return response
            messages.success(request, "Item created")
            return redirect("items_list")
        ctx = {"form": form, "is_edit": False, "excluded_fields": EXCLUDED_FIELDS}
        if request.headers.get("HX-Request"):
            response = render(request, self.template_name, ctx)
            response["HX-Retarget"] = "#item-form"
            return response
        return render(request, self.template_name, ctx)


class ItemEditView(View):
    """Edit an existing item.

    Template: inventory/item_form.html.
    """

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
            form = ItemForm(instance=item)
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
            form = ItemForm(request.POST, instance=item)
        except (DatabaseError, ValueError):
            logger.exception("Error loading form for item %s", pk)
            messages.error(request, "Unable to load item")
            return redirect("items_list")
        if form.is_valid():
            try:
                form.save()
                item_service.get_all_items_with_stock.clear()
                item_service.get_distinct_departments_from_items.clear()
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
    """Display detailed information and stock for an item.

    Template: inventory/item_detail.html.
    """

    template_name = "inventory/item_detail.html"

    def get(self, request, pk: int):
        try:
            details = item_service.get_item_details(pk)
        except (DatabaseError, ValueError):  # pragma: no cover - defensive
            logger.exception("Error retrieving item %s", pk)
            raise Http404("Item not found")
        if not details:
            raise Http404("Item not found")
        tabs = [
            {
                "id": "details",
                "title": "Details",
                "template": "inventory/_item_details.html",
            },
            {
                "id": "notes",
                "title": "Notes",
                "template": "inventory/_item_notes.html",
            },
        ]
        ctx = {"item": details, "tabs": tabs}
        return render(request, self.template_name, ctx)


class ItemDeleteView(View):
    """Confirm and process deletion or deactivation of an item.

    Template: inventory/item_confirm_delete.html.
    """

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


class ItemSearchView(TemplateView):
    """Return item ``<option>`` elements for autocomplete widgets.

    GET param `q` supplies the search term. If absent, the first GET
    value with a key ending in "item" is used. Template:
    inventory/_item_options.html.
    """

    template_name = "inventory/_item_options.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query = (self.request.GET.get("q") or "").strip()
        if not query:
            for key, val in self.request.GET.items():
                if key.endswith("item"):
                    query = val
                    break
        items = Item.objects.filter(name__icontains=query)[:20]
        ctx["items"] = items
        return ctx


class ItemsBulkUploadView(View):
    """Bulk create items from an uploaded CSV file.

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
