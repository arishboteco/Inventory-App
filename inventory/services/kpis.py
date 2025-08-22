from datetime import timedelta

from django.db.models import F, Sum
from django.utils import timezone

from inventory.models import Item, StockTransaction


def stock_value():
    """Total stock value based on current stock quantities."""
    return Item.objects.aggregate(total=Sum("current_stock"))["total"] or 0


def receipts_last_7_days():
    """Total quantity received in the past 7 days."""
    week_ago = timezone.now() - timedelta(days=7)
    return (
        StockTransaction.objects.filter(
            transaction_type="RECEIVING", transaction_date__gte=week_ago
        ).aggregate(total=Sum("quantity_change"))["total"]
        or 0
    )


def issues_last_7_days():
    """Total quantity issued in the past 7 days."""
    week_ago = timezone.now() - timedelta(days=7)
    total = (
        StockTransaction.objects.filter(
            transaction_type="ISSUE", transaction_date__gte=week_ago
        ).aggregate(total=Sum("quantity_change"))["total"]
        or 0
    )
    return abs(total)


def low_stock_count():
    """Number of items below their reorder point."""
    return Item.objects.filter(
        reorder_point__isnull=False, current_stock__lt=F("reorder_point")
    ).count()
