from datetime import timedelta
from typing import List, Tuple

from django.db.models import F, Sum
from django.db.models.functions import TruncDate
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


def stock_trend_last_7_days() -> Tuple[List[str], List[float]]:
    """Return labels and net stock change for the past 7 days."""
    today = timezone.now().date()
    start = today - timedelta(days=6)
    qs = (
        StockTransaction.objects.filter(transaction_date__date__gte=start)
        .annotate(day=TruncDate("transaction_date"))
        .values("day")
        .annotate(total=Sum("quantity_change"))
    )
    data = {}
    for row in qs:
        day = row["day"]
        if hasattr(day, "date"):
            day = day.date()
        data[day] = float(row["total"])
    labels: List[str] = []
    values: List[float] = []
    for i in range(7):
        day = start + timedelta(days=i)
        labels.append(day.strftime("%Y-%m-%d"))
        values.append(data.get(day, 0.0))
    return labels, values
