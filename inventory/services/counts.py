"""Lightweight count helpers for dashboard navigation."""

from inventory.models import Item, Supplier, PurchaseOrder


def item_count() -> int:
    """Return total number of items."""
    return Item.objects.count()


def supplier_count() -> int:
    """Return total number of suppliers."""
    return Supplier.objects.count()


def pending_po_count() -> int:
    """Return count of purchase orders not yet completed or cancelled."""
    return PurchaseOrder.objects.filter(status__in=["DRAFT", "ORDERED", "PARTIAL"]).count()
