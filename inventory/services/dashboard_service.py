from django.db.models import F

from inventory.models import Item

from .item_service import get_unit_display_name


def get_low_stock_items():
    """Return items whose current stock is below their reorder point."""
    qs = (
        Item.objects
        .only("name", "unit_id", "current_stock", "reorder_point")
        .filter(
            reorder_point__isnull=False,
            current_stock__lt=F("reorder_point"),
            is_active=True,
        )
    )
    if hasattr(Item, "is_placeholder"):
        qs = qs.filter(is_placeholder=False)

    # Add unit display names in Python instead of database annotation
    items = list(qs.order_by("name"))
    for item in items:
        item.uom = get_unit_display_name(item.unit_id)
        item.unit = item.unit_id

    return items
