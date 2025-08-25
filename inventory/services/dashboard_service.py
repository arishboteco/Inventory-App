from django.db.models import F

from inventory.models import Item


def get_low_stock_items():
    """Return items whose current stock is below their reorder point."""
    qs = (
        Item.objects.annotate(uom=F("base_unit"), unit=F("base_unit"))
        .only("name", "base_unit", "current_stock", "reorder_point")
        .filter(
            reorder_point__isnull=False,
            current_stock__lt=F("reorder_point"),
            is_active=True,
        )
    )
    if hasattr(Item, "is_placeholder"):
        qs = qs.filter(is_placeholder=False)
    return qs.order_by("name")
