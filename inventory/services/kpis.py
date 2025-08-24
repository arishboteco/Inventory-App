from datetime import timedelta
from decimal import Decimal
from typing import List, Tuple

from django.db.models import Avg, Count, F, Max, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from inventory.models import GRNItem, Indent, Item, PurchaseOrder, StockTransaction


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


def low_stock_items(limit: int = 5) -> List[str]:
    """Return names of items that are below their reorder point."""
    qs = Item.objects.filter(
        reorder_point__isnull=False,
        current_stock__lt=F("reorder_point"),
        is_active=True,
    )
    if hasattr(Item, "is_placeholder"):
        qs = qs.filter(is_placeholder=False)
    qs = qs.order_by("name")
    return list(qs.values_list("name", flat=True)[:limit])


def high_price_purchases(threshold: Decimal) -> List[GRNItem]:
    """Return recent GRN items priced above historical averages.

    Args:
        threshold: Percentage represented as a decimal (e.g., ``Decimal('0.1')``
            for 10%). A GRN item's price must exceed ``avg_price * (1 + threshold)``
            to be flagged.
    """

    cutoff = timezone.now() - timedelta(days=30)
    flagged: List[GRNItem] = []
    for grn_item in GRNItem.objects.filter(
        grn__received_date__gte=cutoff
    ).select_related("po_item__item"):
        avg_price = (
            GRNItem.objects.filter(po_item__item=grn_item.po_item.item)
            .exclude(pk=grn_item.pk)
            .aggregate(avg=Avg("unit_price_at_receipt"))["avg"]
        )
        if avg_price and grn_item.unit_price_at_receipt > avg_price * (1 + threshold):
            flagged.append(grn_item)
    return flagged


def pending_po_status_counts() -> dict:
    """Return counts of purchase orders by pending status."""
    qs = PurchaseOrder.objects.filter(status__in=["DRAFT", "ORDERED", "PARTIAL"])
    counts = {
        row["status"]: row["total"]
        for row in qs.values("status").annotate(total=Count("po_id"))
    }
    return {status: counts.get(status, 0) for status in ["DRAFT", "ORDERED", "PARTIAL"]}


def pending_indent_counts() -> dict:
    """Return counts of indents that are not completed or cancelled."""
    qs = Indent.objects.filter(status__in=["PENDING", "SUBMITTED", "PROCESSING"])
    counts = {
        row["status"]: row["total"]
        for row in qs.values("status").annotate(total=Count("indent_id"))
    }
    return {
        status: counts.get(status, 0)
        for status in ["PENDING", "SUBMITTED", "PROCESSING"]
    }


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


def stale_items(days: int = 30, limit: int = 5) -> List[str]:
    """Return items without recent stock activity.

    Args:
        days: Number of days to consider an item active. Transactions older
            than this are ignored.
        limit: Maximum number of item names to return.
    """

    cutoff = timezone.now() - timedelta(days=days)
    qs = (
        Item.objects.annotate(last=Max("stocktransaction__transaction_date"))
        .filter(Q(last__lt=cutoff) | Q(last__isnull=True))
        .order_by("name")
    )
    return list(qs.values_list("name", flat=True)[:limit])
