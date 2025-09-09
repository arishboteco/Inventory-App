import logging

from django.contrib import messages
from django.db import DatabaseError, IntegrityError
from django.db.models import BooleanField, Case, F, Value, When, Q
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
    # Eager load related FK objects to avoid per-row queries during table render
    qs = qs.select_related("unit", "category", "preferred_supplier")
    # Avoid N+1 on departments badges
    qs = qs.prefetch_related("departments")
    filters = {
        "active": "is_active",
        "category": "category__category",
        "subcategory": "category__sub_category",
        # Department handled below (accept ID or name; supports multi-select)
        "supplier": "preferred_supplier_id",
        "base_unit": "unit__base_unit",
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
    # Department filter: accept IDs or names; support multi-select (__in)
    raw_vals = request.GET.getlist("department")
    if len(raw_vals) == 1 and "," in (raw_vals[0] or ""):
        raw_vals = [v.strip() for v in raw_vals[0].split(",")]
    dep_vals = [v for v in (raw_vals or []) if str(v).strip()]

    if dep_vals:
        # Resolve any names to IDs using case-insensitive match; keep numeric IDs as-is
        id_ints = [int(v) for v in dep_vals if str(v).isdigit()]
        name_vals = [v for v in dep_vals if not str(v).isdigit()]
        try:
            q_dep = Q(department_id__in=id_ints)
            for nm in name_vals:
                q_dep |= Q(name__iexact=nm)
            resolved_ids = list(
                Department.objects.filter(q_dep).values_list("department_id", flat=True)
            )
        except Exception:  # pragma: no cover - defensive
            resolved_ids = id_ints  # best-effort fallback
        if resolved_ids:
            qs = qs.filter(departments__department_id__in=resolved_ids).distinct()
            params["department"] = ",".join(dep_vals)
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
        # Build a base querystring (excluding page) for use in sort links / pagination
        try:
            querystring = list_utils.build_querystring(request)
        except Exception:  # pragma: no cover - defensive
            querystring = ""

        form = ItemForm(request.POST) if request.method == "POST" else ItemForm()
        bulk_form = BulkUploadForm()

        suppliers = Supplier.objects.filter(is_active=True).order_by("name")
        departments_for_form = Department.objects.all().order_by("name")
        inline_units = UnitsService.get_unit_choices_for_forms()
        inline_categories = CategoriesService.get_category_choices_for_forms()

        ctx.update(params)
        ctx.update(category_ctx)
        ctx.update(table_ctx)
        stats = {}
        try:
            stats["total_active"] = kpis.total_active_items()
        except Exception:  # pragma: no cover - defensive
            stats["total_active"] = 0
        try:
            stats["low_stock_percentage"] = kpis.low_stock_percentage()
        except Exception:  # pragma: no cover - defensive
            stats["low_stock_percentage"] = 0
        try:
            stats["avg_days_since_last_purchase"] = (
                kpis.average_days_since_last_purchase()
            )
        except Exception:  # pragma: no cover - defensive
            stats["avg_days_since_last_purchase"] = 0
        try:
            stats["stock_value_on_hand"] = kpis.stock_value_on_hand()
        except Exception:  # pragma: no cover - defensive
            stats["stock_value_on_hand"] = 0
        try:
            stats["fastest_movers"] = kpis.fastest_movers_last_7_days()
        except Exception:  # pragma: no cover - defensive
            stats["fastest_movers"] = []

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
                "predictive_filter_names": [
                    "category",
                    "base_unit",
                    "supplier",
                    "department",
                ],
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
                "list_url": reverse("root"),
                "list_title": "Dashboard",
                "current_title": "Inventory",
                "querystring": querystring,
            }
        )
        return ctx


class ItemsTableView(TemplateView):
    """Render the paginated table of items."""

    def _get_queryset(self):
        qs, params = _filter_and_sort_items(self.request)
        self._filter_params = params
        return qs

    def get_template_names(self):  # pragma: no cover - simple logic
        return ["inventory/_items_table.html"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self._get_queryset()
        page_obj, per_page = list_utils.paginate(self.request, qs)
        ctx.update(self._filter_params)
        try:
            querystring = list_utils.build_querystring(self.request)
        except Exception:  # pragma: no cover - defensive
            querystring = ""
        ctx.update({"page_obj": page_obj, "page_size": per_page, "querystring": querystring})
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
