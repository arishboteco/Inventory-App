import logging

from django.contrib import messages
from django.core.cache import cache
from django.db import DatabaseError, IntegrityError
from django.db.models import (
    BooleanField,
    Case,
    Count,
    F,
    Prefetch,
    Q,
    Value,
    When,
)
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView

from inventory.services.item_service import get_unit_display_name
from inventory.services.units_service import UnitsService

from ...forms.bulk_forms import BulkUploadForm
from ...forms.item_forms import ItemForm
from ...models import Category, Item, Supplier, Unit
from ...models.departments import Department
from ...models.orders import PurchaseOrderItem
from ...services import category_filters, kpis, list_utils
from ...services.categories_service import CategoriesService
from .constants import EXCLUDED_FIELDS

logger = logging.getLogger(__name__)


def _basic_item_filters(request, qs=None):
    """Apply lightweight filtering based on request params without annotations."""
    qs = qs or Item.objects.all()
    # Allow multi-select by passing repeated params or comma-separated values
    filters = {
        "active": "is_active",
        "category": "category__category",
        "subcategory": "category__sub_category",
        # Department handled below (accept ID or name; supports multi-select)
        "supplier": "preferred_supplier_id",
        "base_unit": "unit__base_unit",
    }
    qs, params = list_utils.apply_filters_sort(
        request,
        qs,
        search_fields=["name", "category__category", "category__sub_category"],
        filter_fields=filters,
        allowed_sorts=[],
        default_sort="item_id",
    )
    params.pop("sort", None)
    params.pop("direction", None)

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
    if dep_vals:
        params["department"] = dep_vals

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


def _filter_and_sort_items(request, qs=None):
    """Return items queryset and filter metadata from request params."""
    qs, params = _basic_item_filters(request, qs)
    qs = qs.annotate(
        stock_ok=Case(
            When(current_stock__gte=F("reorder_point"), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )
    # Eager load related FK objects; restrict columns to those used in the table
    qs = (
        qs.select_related("unit", "category", "preferred_supplier")
        .only(
            "item_id",
            "name",
            "unit",
            "category",
            "current_stock",
            "reorder_point",
            "is_active",
            "preferred_supplier",
        )
        .defer("notes")
    )
    # Avoid N+1 on departments badges and limit fields fetched for departments
    qs = qs.prefetch_related(
        Prefetch(
            "departments",
            queryset=Department.objects.only("department_id", "name").order_by("name"),
        )
    )
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
    qs, sort_params = list_utils.apply_filters_sort(
        request,
        qs,
        search_fields=None,
        filter_fields=None,
        allowed_sorts=allowed_sorts,
        default_sort="name",
    )
    params.update(sort_params)
    return qs, params


@require_GET
def distinct_values(request, field):
    """Return distinct values for a given column respecting current filters."""
    qs, _ = _basic_item_filters(request)
    CACHE_TTL = 30
    cache_key = f"distinct:{field}:{request.GET.urlencode()}"
    cached = cache.get(cache_key)
    if cached is not None:
        resp = JsonResponse(cached, safe=False)
        resp["Cache-Control"] = f"max-age={CACHE_TTL}"
        return resp
    try:
        limit = int(request.GET.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, 100))
    try:
        page = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    page = max(page, 1)
    offset = (page - 1) * limit
    field_map = {
        "name": "name",
        "active": "is_active",
    }
    if field == "stock_status":
        data = []
        if qs.filter(
            current_stock__lt=F("reorder_point"), current_stock__gt=0
        ).exists():
            data.append({"value": "low", "label": "Low"})
        if qs.filter(current_stock__lte=0).exists():
            data.append({"value": "out", "label": "Out"})
        if qs.filter(current_stock__gte=F("reorder_point")).exists():
            data.append({"value": "normal", "label": "In Stock"})
        return JsonResponse(data, safe=False)
    if field == "department":
        vals = (
            Department.objects.filter(items__in=qs)
            .order_by("name")
            .values_list("department_id", "name")
            .distinct()
        )[offset : offset + limit]
        data = [{"value": str(pk), "label": name} for pk, name in vals if pk]
    elif field == "category":
        vals = (
            Category.objects.filter(item__in=qs)
            .order_by("category")
            .values_list("category", flat=True)
            .distinct()
        )[offset : offset + limit]
        data = [{"value": str(v), "label": str(v)} for v in vals if v not in [None, ""]]
    elif field == "unit":
        vals = (
            Unit.objects.filter(item__in=qs)
            .order_by("base_unit")
            .values_list("base_unit", flat=True)
            .distinct()
        )[offset : offset + limit]
        data = [{"value": str(v), "label": str(v)} for v in vals if v not in [None, ""]]
    else:
        lookup = field_map.get(field)
        if not lookup:
            return JsonResponse([], safe=False)
        vals = (qs.order_by(lookup).values_list(lookup, flat=True).distinct())[
            offset : offset + limit
        ]
        data = [{"value": str(v), "label": str(v)} for v in vals if v not in [None, ""]]
    cache.set(cache_key, data, CACHE_TTL)
    resp = JsonResponse(data, safe=False)
    resp["Cache-Control"] = f"max-age={CACHE_TTL}"
    return resp


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
                messages.success(
                    request,
                    f'Item "{item.name}" created successfully!',
                    extra_tags="toast",
                )
                return redirect("items_list")
            except (DatabaseError, IntegrityError) as e:
                logger.error("Database error creating item: %s", e)
                if (request.POST.get("partial") or "").lower() in {"1", "true", "yes"}:
                    return JsonResponse({"ok": False, "message": str(e)}, status=400)
                messages.error(request, f"Error creating item: {e}", extra_tags="toast")
            except Exception as e:  # pragma: no cover - defensive
                logger.error("Unexpected error creating item: %s", e)
                if (request.POST.get("partial") or "").lower() in {"1", "true", "yes"}:
                    return JsonResponse({"ok": False, "message": str(e)}, status=400)
                messages.error(request, f"Unexpected error: {e}", extra_tags="toast")
        else:
            if (request.POST.get("partial") or "").lower() in {"1", "true", "yes"}:
                return JsonResponse(
                    {"ok": False, "message": form.errors.as_json()}, status=400
                )
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}", extra_tags="toast")

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

        # Narrow columns for chooser lists; these change rarely so we can cheaply fetch
        suppliers = (
            Supplier.objects.filter(is_active=True)
            .only("supplier_id", "name")
            .order_by("name")
        )
        departments_for_form = Department.objects.only(
            "department_id", "name"
        ).order_by("name")
        inline_units = UnitsService.get_unit_choices_for_forms()
        inline_categories = CategoriesService.get_category_choices_for_forms()

        ctx.update(params)
        ctx.update(category_ctx)
        ctx.update(table_ctx)
        kpi_qs, _ = _basic_item_filters(request)
        stats = {}
        try:
            active_qs = kpi_qs.filter(is_active=True)
            active_count = active_qs.count()
            stats["low_stock_count"] = active_qs.filter(
                current_stock__isnull=False,
                reorder_point__isnull=False,
                current_stock__lt=F("reorder_point"),
            ).count()
            stats["active_items"] = active_count
            stats["low_stock_pct"] = (
                round(stats["low_stock_count"] / active_count * 100, 1)
                if active_count
                else 0
            )
            stats["avg_days_since_purchase"] = round(
                kpis.average_days_since_last_purchase(), 1
            )
            stats["stock_value"] = kpis.stock_value_on_hand()
        except Exception:  # pragma: no cover - defensive
            stats["low_stock_count"] = 0
            stats["active_items"] = 0
            stats["low_stock_pct"] = 0
            stats["avg_days_since_purchase"] = 0
            stats["stock_value"] = 0

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
                # Enable predictive multi-select enhancement for filters
                "predictive_filter_names": [
                    "category",
                    "subcategory",
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
        if self.request.headers.get("HX-Request"):
            return ["inventory/items_table_htmx.html"]
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
        ctx.update(
            {
                "page_obj": page_obj,
                "page_size": per_page,
                "querystring": querystring,
                "items_list_url": reverse("items_list"),
                "items_table_url": reverse("items_table"),
            }
        )
        ctx.update(category_filters.resolve_category_filters(self.request))
        ctx["filters"] = category_filters.build_filters(self.request)
        ctx["predictive_filter_names"] = [
            "category",
            "subcategory",
            "base_unit",
            "supplier",
            "department",
        ]
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
        # Accept multiple parameter shapes from different widgets/contexts
        # 1) explicit ?q=
        # 2) htmx input submits value under "value"
        # 3) formset input name ending with "item" (e.g., items-0-item)
        query = (self.request.GET.get("q") or "").strip()
        if not query:
            query = (self.request.GET.get("value") or "").strip()
        if not query:
            for key, val in self.request.GET.items():
                if str(key).endswith("item"):
                    query = str(val).strip()
                    break
        qs = Item.objects.only("item_id", "name").filter(name__icontains=query)
        # Optional department restriction
        dep_raw = (
            self.request.GET.get("department")
            or self.request.GET.get("department_id")
            or self.request.GET.get("department-ui")
        )
        if dep_raw:
            try:
                if str(dep_raw).isdigit():
                    dep_id = int(dep_raw)
                    qs = (
                        qs.annotate(_ndept=Count("departments", distinct=True))
                        .filter(Q(_ndept=0) | Q(departments__department_id=dep_id))
                        .distinct()
                    )
                else:
                    name = str(dep_raw)
                    qs = (
                        qs.annotate(_ndept=Count("departments", distinct=True))
                        .filter(Q(_ndept=0) | Q(departments__name__iexact=name))
                        .distinct()
                    )
            except Exception:
                pass
        items = qs[:20]
        ctx["items"] = items
        return ctx


@require_GET
def item_meta(request, item_id: int):
    """Return item metadata for predictive widgets and recipe lookups.

    Includes the base-unit label, category info, and a suggested purchase
    order id when available.
    """
    try:
        item = (
            Item.objects.select_related("unit", "category")
            .only(
                "item_id",
                "name",
                "unit",
                "category",
                "last_purchase_price",
                "initial_purchase_price",
                "current_stock",
            )
            .get(pk=item_id)
        )
    except Item.DoesNotExist:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)
    unit_display = get_unit_display_name(item.unit_id) if item.unit_id else ""
    base_unit_display = (
        UnitsService.get_base_unit_display(item.unit_id) if item.unit_id else ""
    )
    uinfo = (
        UnitsService.get_unit_info(item.unit_id)
        if item.unit_id
        else {"conversion_factor": 1.0}
    )
    conv = float(uinfo.get("conversion_factor") or 1.0)
    price_source = item.last_purchase_price or item.initial_purchase_price or 0
    last_price = float(price_source or 0)
    cost_per_base = float(UnitsService.cost_per_base_for_item(item))
    cat = getattr(item, "category", None)
    category = getattr(cat, "category", "")
    subcategory = getattr(cat, "sub_category", "")
    # Suggest the latest PO that references this item
    po_suggestion = None
    try:
        poi = (
            PurchaseOrderItem.objects.select_related("purchase_order")
            .filter(item_id=item.item_id)
            .order_by("-purchase_order__order_date")
            .first()
        )
        if poi and poi.purchase_order_id:
            po_suggestion = poi.purchase_order_id
    except Exception:
        po_suggestion = None
    data = {
        "ok": True,
        "item_id": item.item_id,
        "name": item.name,
        "unit": unit_display,
        "category": category,
        "subcategory": subcategory,
        "po_suggestion": po_suggestion,
        "base_unit": base_unit_display,
        "last_purchase_price": last_price,
        "conversion_factor": conv,
        "cost_per_base_unit": cost_per_base,
        "current_stock": float(item.current_stock or 0),
    }
    return JsonResponse(data)
