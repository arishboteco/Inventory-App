"""Utility functions for stock-related queries."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from django.db.models import Case, CharField, F, Value, When

from inventory.models import Item

from .units_service import UnitsService


@lru_cache(maxsize=1)
def get_low_stock_items() -> List[Item]:
    """Return items whose current stock is below their reorder point.

    The returned list is cached to reduce database load. The list is annotated
    with ``uom`` containing the purchase unit display name for each item. Use
    :func:`get_low_stock_items.clear` to invalidate the cache after any
    operation that mutates item stock levels or reorder points.
    """
    qs = Item.objects.only("name", "unit_id", "current_stock", "reorder_point").filter(
        reorder_point__isnull=False,
        current_stock__lt=F("reorder_point"),
        is_active=True,
    )
    if hasattr(Item, "is_placeholder"):
        qs = qs.filter(is_placeholder=False)

    units_map = {u["unit_id"]: u["purchase_unit"] for u in UnitsService.get_all_units()}
    whens = [When(unit_id=unit_id, then=Value(uom)) for unit_id, uom in units_map.items()]

    qs = qs.annotate(
        uom=Case(
            *whens,
            default=Value(""),
            output_field=CharField(),
        ),
    ).order_by("name")

    return list(qs)


# expose a ``clear`` method consistent with other cached helpers
get_low_stock_items.clear = get_low_stock_items.cache_clear  # type: ignore[attr-defined]
