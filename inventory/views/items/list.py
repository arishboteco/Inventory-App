import logging

from django.contrib import messages
from django.db import DatabaseError, IntegrityError
from django.db.models import BooleanField, Case, F, Value, When
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from inventory.services.item_service import get_unit_display_name

from ...forms.bulk_forms import BulkUploadForm
from ...forms.item_forms import ItemForm
from ...models import Item, Supplier
from ...models.departments import Department
from ...services import category_filters, kpis, list_utils
from ...services.categories_service import CategoriesService
from ...services.units_service import UnitsService
from .constants import EXCLUDED_FIELDS

logger = logging.getLogger(__name__)


def _filter_and_sort_items(request, qs=None):
    """Return items queryset and filter metadata from request params."""
    qs = qs or Item.objects.all()
    qs = qs.annotate(
        stock_ok=Case(
            When(current_stock__gte=F("reorder_point"), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )
    # Avoid N+1 on departments badges
    qs = qs.prefetch_related("departments")
    filters = {
        "active": "is_active",
        "category": "category__category",
        "subcategory": "category__sub_category",
        "department": "departments__name",
    }
    allowed_sorts = {
        "item_id",
        "name",
        "unit__base_unit",
        "category__category",
        "category__sub_category",
        "current_stock",
        "reorder_point",
        "is_active",
        "initial_purchase_price",
        "last_purchase_price",
    }
    qs, params = list_utils.apply_filters_sort(
        request,
        qs,
        search_fields=["name", "category__category", "category__sub_category"],
        filter_fields=filters,
        allowed_sorts=allowed_sorts,
        default_sort="name",
    )
    # Apply stock status filter if present
    stock_status = (request.GET.get("stock_status") or "").strip().lower()
    if stock_status == "low":
        qs = qs.filter(current_stock__lt=F("reorder_point"), current_stock__gt=0)
    elif stock_status == "out":
        qs = qs.filter(current_stock__lte=0)
    elif stock_status == "normal":
        qs = qs.filter(current_stock__gte=F("reorder_point"))
    if stock_status:
        params.update({"stock_status": stock_status})
    # Optional visibility toggles without changing current defaults
    show_inactive = (request.GET.get("show_inactive") or "").lower() in {
        "1",
        "true",
        "on",
    }
    active_only = (request.GET.get("active_only") or "").lower() in {
        "1",
        "true",
        "on",
    }
    if show_inactive:
        qs = qs.filter(is_active=False)
    if active_only:
        qs = qs.filter(is_active=True)
    params.update(
        {
            "show_inactive": "1" if show_inactive else "",
            "active_only": "1" if active_only else "",
        }
    )
    return qs, params


class ItemsListView(TemplateView):
    """Show item filters and options for the list view."""

    template_name = "inventory/items_list.html"

    def post(self, request, *args, **kwargs):
        """Handle inline item creation via POST request."""
        form = ItemForm(request.POST)

        if form.is_valid():
            try:
                item = form.save()
                if (request.POST.get("partial") or "").lower() in {"1", "true", "yes"}:
                    return JsonResponse(
                        {"ok": True, "message": "Item created", "id": item.item_id}
                    )
                messages.success(request, f'Item "{item.name}" created successfully!')
                return redirect("items_list")
            except (DatabaseError, IntegrityError) as e:
                logger.error("Database error creating item: %s", e)
                if (request.POST.get("partial") or "").lower() in {"1", "true", "yes"}:
                    return JsonResponse({"ok": False, "message": str(e)}, status=400)
                messages.error(request, f"Error creating item: {e}")
            except Exception as e:  # pragma: no cover - defensive
                logger.error("Unexpected error creating item: %s", e)
                if (request.POST.get("partial") or "").lower() in {"1", "true", "yes"}:
                    return JsonResponse({"ok": False, "message": str(e)}, status=400)
                messages.error(request, f"Unexpected error: {e}")
        else:
            if (request.POST.get("partial") or "").lower() in {"1", "true", "yes"}:
                return JsonResponse(
                    {"ok": False, "message": form.errors.as_json()}, status=400
                )
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        category_ctx = category_filters.resolve_category_filters(request)
        qs, params = _filter_and_sort_items(request)
        page_obj, per_page = list_utils.paginate(request, qs)
        table_ctx = {**params, "page_obj": page_obj, "page_size": per_page}

        form = ItemForm(request.POST) if request.method == "POST" else ItemForm()
        bulk_form = BulkUploadForm()

        suppliers = Supplier.objects.filter(is_active=True).order_by("name")
        departments_for_form = Department.objects.all().order_by("name")
        inline_units = UnitsService.get_unit_choices_for_forms()
        inline_categories = CategoriesService.get_category_choices_for_forms()

        ctx.update(params)
        ctx.update(category_ctx)
        ctx.update(table_ctx)
        try:
            pending_po_counts = kpis.pending_po_status_counts()
            pending_orders = sum(pending_po_counts.values())
        except Exception:  # pragma: no cover - defensive
            pending_orders = 0
        try:
            total_value = kpis.stock_value()
        except Exception:  # pragma: no cover - defensive
            total_value = 0
        stats = {
            "low_stock_count": kpis.low_stock_count(),
            "pending_orders": pending_orders,
            "total_value": total_value,
        }

        filters_list = category_filters.build_filters(request)

        categories_val = category_ctx.get("categories", [])
        subcategories_val = category_ctx.get("subcategories", [])
        if not request.GET.get("category"):
            categories_val = []
        if not request.GET.get("subcategory"):
            subcategories_val = []

        ctx.update(
            {
                "page_size": per_page,
                "filters": filters_list,
                "export_url": reverse("items_export"),
                "stats": stats,
                "form": form,
                "bulk_form": bulk_form,
                "suppliers": suppliers,
                "departments_for_form": departments_for_form,
                "excluded_fields": EXCLUDED_FIELDS,
                "inline_units": inline_units,
                "inline_categories": inline_categories,
                "categories": categories_val,
                "subcategories": subcategories_val,
                "list_url": reverse("dashboard"),
                "list_title": "Dashboard",
                "current_title": "Inventory",
            }
        )
        return ctx


class ItemsTableView(TemplateView):
    """Render the paginated table of items."""

    template_name = "components/items_table.html"

    def _get_queryset(self):
        qs, params = _filter_and_sort_items(self.request)
        self._filter_params = params
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self._get_queryset()
        page_obj, per_page = list_utils.paginate(self.request, qs)
        ctx.update(self._filter_params)
        layout = (self.request.GET.get("layout") or "table").lower()
        ctx.update({"page_obj": page_obj, "page_size": per_page, "layout": layout})
        return ctx


class ItemsExportView(TemplateView):
    """Export the filtered item list as CSV."""

    def get(self, request):
        qs, _ = _filter_and_sort_items(request)
        headers = [
            "ID",
            "Name",
            "Unit",
            "Current Stock",
            "Reorder Point",
            "Active",
        ]

        def row(item: Item):
            return [
                item.item_id,
                item.name,
                get_unit_display_name(item.unit_id),
                item.current_stock,
                item.reorder_point,
                item.is_active,
            ]

        return list_utils.export_as_csv(qs, headers, row, "items.csv")


class ItemSearchView(TemplateView):
    """Return item ``<option>`` elements for autocomplete widgets."""

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
