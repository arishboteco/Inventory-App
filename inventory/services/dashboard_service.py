from django.db.models import F, Case, CharField, Value, When

from inventory.models import Item

from .units_service import UnitsService


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

    units_map = {
        u["unit_id"]: u["purchase_unit"]
        for u in UnitsService.get_all_units()
    }
    whens = [When(unit_id=k, then=Value(v)) for k, v in units_map.items()]
    qs = qs.annotate(
        unit=F("unit_id"),
        uom=Case(
            *whens,
            default=Value(""),
            output_field=CharField(),
        ),
    )
    return qs.order_by("name")
