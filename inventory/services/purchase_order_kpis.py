"""Purchase Order KPIs and analytics functions."""

from datetime import timedelta
from decimal import Decimal
from typing import Dict, List

from django.db.models import (
    Avg,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Sum,
)
from django.utils import timezone

from inventory.models import PurchaseOrder, PurchaseOrderItem


def get_po_summary_kpis() -> Dict[str, any]:
    """Get comprehensive KPIs for purchase orders list page.

    Returns a dictionary with:
    - total_pos: Total count of all purchase orders
    - pending_count: Count of orders awaiting receipt (ORDERED + PARTIAL)
    - completed_count: Count of completed orders
    - cancelled_count: Count of cancelled orders
    - total_value: Total monetary value of all PO items
    - pending_value: Value of orders not yet completed
    - overdue_count: Orders past expected delivery date
    - avg_lead_time: Average days from order to completion
    """
    now = timezone.now().date()

    # Basic counts by status
    total_pos = PurchaseOrder.objects.count()
    pending_count = PurchaseOrder.objects.filter(
        status__in=["ORDERED", "PARTIAL"]
    ).count()
    completed_count = PurchaseOrder.objects.filter(status="COMPLETE").count()
    cancelled_count = PurchaseOrder.objects.filter(status="CANCELLED").count()
    draft_count = PurchaseOrder.objects.filter(status="DRAFT").count()

    # Value calculations
    total_value = PurchaseOrderItem.objects.aggregate(
        total=Sum(
            ExpressionWrapper(
                F("quantity_ordered") * F("unit_price"),
                output_field=DecimalField(max_digits=19, decimal_places=2),
            )
        )
    )["total"] or Decimal("0")

    pending_value = PurchaseOrderItem.objects.filter(
        purchase_order__status__in=["DRAFT", "ORDERED", "PARTIAL"]
    ).aggregate(
        total=Sum(
            ExpressionWrapper(
                F("quantity_ordered") * F("unit_price"),
                output_field=DecimalField(max_digits=19, decimal_places=2),
            )
        )
    )["total"] or Decimal("0")

    # Overdue orders (past expected delivery date and not complete)
    overdue_count = PurchaseOrder.objects.filter(
        expected_delivery_date__lt=now,
        status__in=["ORDERED", "PARTIAL"]
    ).count()

    # Average lead time (for completed orders with both dates)
    # Lead time = days from order_date to when status became COMPLETE
    # Since we don't track completion date, use current date as approximation
    # for better accuracy, you'd need to add a completed_date field
    completed_pos = PurchaseOrder.objects.filter(
        status="COMPLETE",
        order_date__isnull=False,
        expected_delivery_date__isnull=False
    )
    avg_lead_time = 0
    if completed_pos.exists():
        lead_times = []
        for po in completed_pos:
            if po.expected_delivery_date and po.order_date:
                days = (po.expected_delivery_date - po.order_date).days
                if days >= 0:  # Only count positive lead times
                    lead_times.append(days)
        avg_lead_time = sum(lead_times) / len(lead_times) if lead_times else 0

    return {
        "total_pos": total_pos,
        "pending_count": pending_count,
        "completed_count": completed_count,
        "cancelled_count": cancelled_count,
        "draft_count": draft_count,
        "total_value": total_value,
        "pending_value": pending_value,
        "overdue_count": overdue_count,
        "avg_lead_time": round(avg_lead_time, 1),
    }


def get_top_suppliers_by_value(limit: int = 5) -> List[Dict[str, any]]:
    """Get top suppliers ranked by total purchase value.

    Args:
        limit: Maximum number of suppliers to return

    Returns:
        List of dicts with supplier name, total value, and order count
    """
    suppliers = (
        PurchaseOrderItem.objects.select_related(
            "purchase_order__supplier"
        )
        .values(
            "purchase_order__supplier__name",
            "purchase_order__supplier_id"
        )
        .annotate(
            total_value=Sum(
                ExpressionWrapper(
                    F("quantity_ordered") * F("unit_price"),
                    output_field=DecimalField(max_digits=19, decimal_places=2),
                )
            ),
            order_count=Count("purchase_order_id", distinct=True)
        )
        .order_by("-total_value")[:limit]
    )

    return [
        {
            "supplier_id": s["purchase_order__supplier_id"],
            "supplier_name": s["purchase_order__supplier__name"],
            "total_value": s["total_value"],
            "order_count": s["order_count"],
        }
        for s in suppliers
    ]


def get_recent_po_trends(days: int = 30) -> Dict[str, any]:
    """Get purchase order trends for recent period.

    Args:
        days: Number of days to look back

    Returns:
        Dictionary with counts and values for the period
    """
    cutoff = timezone.now() - timedelta(days=days)

    recent_pos = PurchaseOrder.objects.filter(order_date__gte=cutoff)

    return {
        "count": recent_pos.count(),
        "total_value": PurchaseOrderItem.objects.filter(
            purchase_order__order_date__gte=cutoff
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("quantity_ordered") * F("unit_price"),
                    output_field=DecimalField(max_digits=19, decimal_places=2),
                )
            )
        )["total"] or Decimal("0"),
        "avg_value": PurchaseOrderItem.objects.filter(
            purchase_order__order_date__gte=cutoff
        ).aggregate(
            avg=Avg(
                ExpressionWrapper(
                    F("quantity_ordered") * F("unit_price"),
                    output_field=DecimalField(max_digits=19, decimal_places=2),
                )
            )
        )["avg"] or Decimal("0"),
    }


def get_items_most_ordered(limit: int = 10) -> List[Dict[str, any]]:
    """Get items that appear most frequently in purchase orders.

    Args:
        limit: Maximum number of items to return

    Returns:
        List of dicts with item name, total quantity ordered, and order count
    """
    items = (
        PurchaseOrderItem.objects.select_related("item")
        .values("item_id", "item__name")
        .annotate(
            total_quantity=Sum("quantity_ordered"),
            order_count=Count("purchase_order_id", distinct=True),
            total_value=Sum(
                ExpressionWrapper(
                    F("quantity_ordered") * F("unit_price"),
                    output_field=DecimalField(max_digits=19, decimal_places=2),
                )
            ),
        )
        .order_by("-order_count")[:limit]
    )

    return [
        {
            "item_id": i["item_id"],
            "item_name": i["item__name"],
            "total_quantity": i["total_quantity"],
            "order_count": i["order_count"],
            "total_value": i["total_value"],
        }
        for i in items
    ]


def get_fulfillment_rate() -> float:
    """Calculate the percentage of POs that are fully received.

    Returns:
        Percentage (0-100) of complete purchase orders
    """
    total = PurchaseOrder.objects.exclude(status="CANCELLED").count()
    if total == 0:
        return 0.0

    complete = PurchaseOrder.objects.filter(status="COMPLETE").count()
    return round((complete / total) * 100, 1)


def get_on_time_delivery_rate() -> float:
    """Calculate percentage of POs received by expected delivery date.

    Note: This is an approximation since we don't track actual delivery dates.
    Uses COMPLETE status as proxy for delivered.

    Returns:
        Percentage (0-100) of on-time deliveries
    """
    today = timezone.now().date()

    # Completed orders with expected delivery dates
    completed_with_dates = PurchaseOrder.objects.filter(
        status="COMPLETE",
        expected_delivery_date__isnull=False
    )

    total_count = completed_with_dates.count()
    if total_count == 0:
        return 0.0

    # Assume orders completed before expected date were on time
    # This is a rough heuristic
    on_time = completed_with_dates.filter(
        expected_delivery_date__gte=today
    ).count()

    return round((on_time / total_count) * 100, 1)
