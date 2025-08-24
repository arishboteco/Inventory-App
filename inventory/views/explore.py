from __future__ import annotations

from django.shortcuts import render
from django.urls import reverse

from ..models import items as models_items
from ..services import list_utils

Item = models_items.Item


def _filter_items(request):
    """Return filtered and sorted queryset of items."""
    qs = Item.objects.all()
    qs, params = list_utils.apply_filters_sort(
        request,
        qs,
        search_fields=["name"],
        filter_fields={"active": "is_active"},
        default_sort="name",
    )
    return qs, params


def explore(request):
    """Display items with optional filters and pagination."""
    qs, params = _filter_items(request)
    page_obj, per_page = list_utils.paginate(request, qs)
    ctx = {
        **params,
        "page_obj": page_obj,
        "page_size": per_page,
        "querystring": list_utils.build_querystring(request),
        "export_url": reverse("explore_export"),
    }
    return render(request, "inventory/explore.html", ctx)


def explore_export(request):
    """Export the filtered items as CSV."""
    qs, _ = _filter_items(request)
    headers = ["ID", "Name", "Base Unit", "Current Stock", "Active"]

    def row(item: Item):
        return [
            item.item_id,
            item.name,
            item.base_unit,
            item.current_stock,
            item.is_active,
        ]

    return list_utils.export_as_csv(qs, headers, row, "items.csv")
