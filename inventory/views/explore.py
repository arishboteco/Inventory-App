from __future__ import annotations

from django.db.models import F
from django.shortcuts import render
from django.urls import reverse

from inventory.services.item_service import get_unit_display_name

from ..models import items as models_items
from ..models.category import Category
from ..services import list_utils

Item = models_items.Item

VALID_SORTS = ["name", "category__category", "current_stock", "reorder_point"]


def _filter_items(request):
    """Return filtered and sorted queryset of items."""
    qs = Item.objects.select_related("unit", "category").all()

    stock_status = request.GET.get("stock_status", "").strip()
    if stock_status == "out":
        qs = qs.filter(current_stock__lte=0)
    elif stock_status == "low":
        qs = qs.filter(current_stock__gt=0, current_stock__lte=F("reorder_point"))
    elif stock_status == "in":
        qs = qs.filter(current_stock__gt=F("reorder_point"))

    category_id = request.GET.get("category", "").strip()
    if category_id:
        qs = qs.filter(category_id=category_id)

    qs, params = list_utils.apply_filters_sort(
        request,
        qs,
        search_fields=["name"],
        filter_fields={"active": "is_active"},
        allowed_sorts=VALID_SORTS,
        default_sort="name",
    )
    params["stock_status"] = stock_status
    params["category"] = category_id
    return qs, params


def explore(request):
    """Display items with optional filters and pagination."""
    qs, params = _filter_items(request)
    page_obj, per_page = list_utils.paginate(request, qs)

    # ABC classification — annotate items on the current page only
    try:
        from ..services.ml import abc_classification

        abc_classes = abc_classification()
    except Exception:
        abc_classes = {}
    for item in page_obj.object_list:
        item.abc_class = abc_classes.get(item.item_id, "")

    # Items with negative stock (for warning banner)
    negative_stock_items = Item.objects.filter(current_stock__lt=0)

    # Categories for filter dropdown
    categories = Category.objects.order_by("category")

    # Sort query: querystring without sort/direction/page (for sort link hrefs)
    sort_params = request.GET.copy()
    sort_params.pop("sort", None)
    sort_params.pop("direction", None)
    sort_params.pop("page", None)
    sort_query = sort_params.urlencode()

    ctx = {
        **params,
        "page_obj": page_obj,
        "page_size": per_page,
        "querystring": list_utils.build_querystring(request),
        "sort_query": sort_query,
        "export_url": reverse("explore_export"),
        "list_url": reverse("root"),
        "list_title": "Dashboard",
        "current_title": "Explore",
        "negative_stock_items": negative_stock_items,
        "categories": categories,
    }
    return render(request, "inventory/explore.html", ctx)


def explore_export(request):
    """Export the filtered items as CSV, respecting all active filters."""
    qs, _ = _filter_items(request)

    try:
        from ..services.ml import abc_classification

        abc_classes = abc_classification()
    except Exception:
        abc_classes = {}

    headers = [
        "ID",
        "Name",
        "Category",
        "Unit",
        "Current Stock",
        "Reorder Point",
        "Stock Status",
        "ABC",
        "Active",
    ]

    def row(item: Item):
        cs = item.current_stock or 0
        rp = item.reorder_point or 0
        if cs <= 0:
            status = "Out of Stock"
        elif cs < rp:
            status = "Low Stock"
        else:
            status = "In Stock"
        return [
            item.item_id,
            item.name,
            getattr(item.category, "category", "") if item.category else "",
            get_unit_display_name(item.unit_id),
            item.current_stock,
            item.reorder_point,
            status,
            abc_classes.get(item.item_id, ""),
            "Active" if item.is_active else "Inactive",
        ]

    return list_utils.export_as_csv(qs, headers, row, "inventory_export.csv")
