from datetime import timedelta
from decimal import Decimal
from typing import List, Tuple

from django.db.models import (
    Avg,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Max,
    OuterRef,
    Q,
    Subquery,
    Sum,
)
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from inventory.models import (
    GRNItem,
    Indent,
    Item,
    PurchaseOrder,
    StockTransaction,
)
from inventory.models.enums import IndentStatus, PurchaseOrderStatus

from .stock_utils import get_low_stock_items


def total_active_items() -> int:
    """Return the number of items currently marked as active."""
    return Item.objects.filter(is_active=True).count()


def low_stock_percentage() -> float:
    """Percentage of active items that are below their reorder point."""
    total = total_active_items()
    if total == 0:
        return 0
    return (low_stock_count() / total) * 100


def average_days_since_last_purchase() -> float:
    """Average number of days since the last purchase for active items."""
    last_receiving = (
        StockTransaction.objects.filter(
            item_id=OuterRef("pk"), transaction_type="RECEIVING"
        )
        .order_by("-transaction_date")
        .values("transaction_date")[:1]
    )
    now = timezone.now()
    qs = (
        Item.objects.filter(is_active=True)
        .annotate(last_purchase=Subquery(last_receiving))
        .values_list("last_purchase", flat=True)
    )
    days = [(now - lp).days for lp in qs if lp is not None]
    return sum(days) / len(days) if days else 0


def fastest_movers_last_7_days(limit: int = 5) -> List[Tuple[str, float]]:
    """Return top N items with highest outgoing quantity in past 7 days."""
    week_ago = timezone.now() - timedelta(days=7)
    qs = (
        StockTransaction.objects.filter(
            transaction_type="ISSUE", transaction_date__gte=week_ago
        )
        .values("item__name")
        .annotate(total=Sum(-F("quantity_change")))
        .order_by("-total")[:limit]
    )
    return [(row["item__name"], float(row["total"])) for row in qs]


def stock_value_on_hand():
    """Monetary value of all stock on hand."""
    total = Item.objects.aggregate(
        total=Sum(
            ExpressionWrapper(
                F("current_stock") * Coalesce("last_purchase_price", 0),
                output_field=DecimalField(max_digits=19, decimal_places=2),
            )
        )
    )["total"]
    return total or 0


def stock_value():  # pragma: no cover - backwards compatibility
    return stock_value_on_hand()


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
    return len(get_low_stock_items())


def low_stock_items(limit: int = 5) -> List[str]:
    """Return names of items that are below their reorder point."""
    return [item.name for item in get_low_stock_items()[:limit]]


def high_price_purchases(threshold: Decimal) -> List[GRNItem]:
    """Return recent GRN items priced above historical averages.

    Args:
        threshold: Percentage represented as a decimal (e.g., ``Decimal('0.1')``
            for 10%). A GRN item's price must exceed ``avg_price * (1 + threshold)``
            to be flagged.
    """

    cutoff = timezone.now() - timedelta(days=30)
    avg_price = (
        GRNItem.objects.filter(po_item__item_id=OuterRef("po_item__item_id"))
        .exclude(pk=OuterRef("pk"))
        .values("po_item__item_id")
        .annotate(avg=Avg("unit_price_at_receipt"))
        .values("avg")[:1]
    )
    qs = (
        GRNItem.objects.filter(grn__received_date__gte=cutoff)
        .select_related("po_item__item")
        .annotate(avg_price=Subquery(avg_price))
        .filter(
            avg_price__isnull=False,
            unit_price_at_receipt__gt=F("avg_price") * (1 + threshold),
        )
    )
    return list(qs)


def pending_po_status_counts() -> dict:
    """Return counts of purchase orders by pending status."""
    pending_statuses = [
        PurchaseOrderStatus.DRAFT,
        PurchaseOrderStatus.SENT,
    ]
    qs = PurchaseOrder.objects.filter(status__in=pending_statuses)
    counts = {
        row["status"]: row["total"]
        for row in qs.values("status").annotate(total=Count("po_id"))
    }
    return {status: counts.get(status, 0) for status in pending_statuses}


def pending_indent_counts() -> dict:
    """Return counts of indents that are not completed or cancelled."""
    pending_statuses = [
        IndentStatus.PENDING,
        IndentStatus.SUBMITTED,
        IndentStatus.PROCESSING,
    ]
    qs = Indent.objects.filter(status__in=pending_statuses)
    counts = {
        row["status"]: row["total"]
        for row in qs.values("status").annotate(total=Count("indent_id"))
    }
    return {status: counts.get(status, 0) for status in pending_statuses}


def stock_trend_last_7_days() -> Tuple[List[str], List[float]]:
    """Return labels and cumulative net stock change for the past 7 days."""
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
    running_total = 0.0
    for i in range(7):
        day = start + timedelta(days=i)
        labels.append(day.strftime("%Y-%m-%d"))
        running_total += data.get(day, 0.0)
        values.append(running_total)
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
