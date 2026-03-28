"""Dashboard KPI calculations for the redesigned dashboard.

All monetary helpers operate on StockTransaction rows and use
``item.last_purchase_price`` as the unit cost proxy.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    Sum,
)
from django.db.models.functions import Coalesce, TruncDate

from inventory.models.items import Item, StockTransaction
from inventory.models.recipes import Recipe, SaleTransaction

# ── helpers ────────────────────────────────────────────────────────────

_VALUE_EXPR = ExpressionWrapper(
    F("quantity_change") * Coalesce(F("item__last_purchase_price"), 0),
    output_field=DecimalField(max_digits=14, decimal_places=2),
)


def _abs_outbound_value(qs):
    """Sum of ``|quantity_change| * unit_price`` for an outbound queryset."""
    total = qs.aggregate(
        total=Coalesce(
            Sum(
                ExpressionWrapper(
                    -F("quantity_change") * Coalesce(F("item__last_purchase_price"), 0),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
            Decimal("0"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["total"]
    return total or Decimal("0")


def _sales_revenue(start, end):
    """Revenue from SaleTransaction rows in the period.

    Uses ``recipe.selling_price * quantity`` as the revenue proxy.
    Falls back to 0 when no sales exist.
    """
    total = (
        SaleTransaction.objects.filter(
            sale_date__date__gte=start,
            sale_date__date__lte=end,
        )
        .select_related("recipe")
        .aggregate(
            total=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F("quantity") * Coalesce(F("recipe__selling_price"), 0),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ),
                Decimal("0"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )["total"]
    )
    return total or Decimal("0")


# ── public KPI functions ───────────────────────────────────────────────


def closing_stock_value():
    """Current on-hand value: ``SUM(current_stock * last_purchase_price)``."""
    total = Item.objects.filter(is_active=True).aggregate(
        total=Coalesce(
            Sum(
                ExpressionWrapper(
                    F("current_stock") * Coalesce(F("last_purchase_price"), 0),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
            Decimal("0"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["total"]
    return total or Decimal("0")


def purchases_total(start, end):
    """Total value of RECEIVING transactions in the period."""
    qs = StockTransaction.objects.filter(
        transaction_type="RECEIVING",
        transaction_date__date__gte=start,
        transaction_date__date__lte=end,
    )
    total = qs.aggregate(
        total=Coalesce(
            Sum(
                ExpressionWrapper(
                    F("quantity_change") * Coalesce(F("item__last_purchase_price"), 0),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
            Decimal("0"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["total"]
    return total or Decimal("0")


def opening_stock_value(start, end):
    """Back-calculated: closing_value − net change during the period."""
    closing = closing_stock_value()
    net = StockTransaction.objects.filter(
        transaction_date__date__gte=start,
        transaction_date__date__lte=end,
    ).aggregate(
        total=Coalesce(
            Sum(_VALUE_EXPR),
            Decimal("0"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )[
        "total"
    ] or Decimal(
        "0"
    )
    return closing - net


def sales_revenue(start, end):
    """Public wrapper – revenue from recipe sales in the period."""
    return _sales_revenue(start, end)


def consumption_total(start, end):
    """Cost value of SALE + ISSUE transactions in the period."""
    qs = StockTransaction.objects.filter(
        transaction_type__in=["SALE", "ISSUE"],
        transaction_date__date__gte=start,
        transaction_date__date__lte=end,
    )
    return _abs_outbound_value(qs)


def consumption_delta(start, end):
    """Percentage change of consumption vs the immediately prior period."""
    span = (end - start).days or 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span - 1)
    current = consumption_total(start, end)
    previous = consumption_total(prev_start, prev_end)
    if previous:
        return float((current - previous) / previous * 100)
    return None


def actual_food_cost_pct(start, end):
    """Consumption / Revenue × 100."""
    revenue = _sales_revenue(start, end)
    if not revenue:
        return None
    return round(float(consumption_total(start, end) / revenue * 100), 1)


def ideal_food_cost_pct(start, end):
    """Weighted ideal FC% based on sales mix.

    Falls back to the simple average of active recipe ``target_food_cost_pct``
    when no SaleTransactions exist in the period.
    """
    sales = (
        SaleTransaction.objects.filter(
            sale_date__date__gte=start,
            sale_date__date__lte=end,
        )
        .select_related("recipe")
        .values_list(
            "recipe__selling_price", "recipe__target_food_cost_pct", "quantity"
        )
    )
    total_revenue = Decimal("0")
    weighted_cost = Decimal("0")
    for selling_price, target_pct, qty in sales:
        sp = Decimal(str(selling_price or 0))
        tp = Decimal(str(target_pct or 30))
        q = Decimal(str(qty or 0))
        rev = sp * q
        total_revenue += rev
        weighted_cost += rev * tp / 100
    if total_revenue:
        return round(float(weighted_cost / total_revenue * 100), 1)
    # Fallback: average target across active recipes
    recipes = Recipe.objects.filter(is_active=True, type="FINAL")
    targets = [
        float(r.target_food_cost_pct)
        for r in recipes
        if r.target_food_cost_pct is not None
    ]
    if targets:
        return round(sum(targets) / len(targets), 1)
    return None


def wastage_total(start, end):
    """Cost value of WASTAGE transactions in the period."""
    qs = StockTransaction.objects.filter(
        transaction_type="WASTAGE",
        transaction_date__date__gte=start,
        transaction_date__date__lte=end,
    )
    return _abs_outbound_value(qs)


def wastage_delta(start, end):
    """Percentage change of wastage vs the immediately prior period."""
    span = (end - start).days or 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span - 1)
    current = wastage_total(start, end)
    previous = wastage_total(prev_start, prev_end)
    if previous:
        return float((current - previous) / previous * 100)
    return None


def daily_trends(start, end):
    """Daily consumption + wastage values for charting.

    Returns ``(labels, consumption_values, wastage_values)`` where each list
    has one entry per calendar day in ``[start, end]``.
    """
    base_qs = StockTransaction.objects.filter(
        transaction_date__date__gte=start,
        transaction_date__date__lte=end,
    )
    cons_qs = (
        base_qs.filter(transaction_type__in=["SALE", "ISSUE"])
        .annotate(day=TruncDate("transaction_date"))
        .values("day")
        .annotate(
            total=Coalesce(
                Sum(
                    ExpressionWrapper(
                        -F("quantity_change")
                        * Coalesce(F("item__last_purchase_price"), 0),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ),
                Decimal("0"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
        .order_by("day")
    )
    waste_qs = (
        base_qs.filter(transaction_type="WASTAGE")
        .annotate(day=TruncDate("transaction_date"))
        .values("day")
        .annotate(
            total=Coalesce(
                Sum(
                    ExpressionWrapper(
                        -F("quantity_change")
                        * Coalesce(F("item__last_purchase_price"), 0),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ),
                Decimal("0"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
        .order_by("day")
    )

    cons_map = {row["day"]: float(row["total"] or 0) for row in cons_qs}
    waste_map = {row["day"]: float(row["total"] or 0) for row in waste_qs}

    labels: list[str] = []
    consumption_values: list[float] = []
    wastage_values: list[float] = []
    num_days = (end - start).days + 1
    for i in range(num_days):
        day = start + timedelta(days=i)
        labels.append(day.strftime("%Y-%m-%d"))
        consumption_values.append(cons_map.get(day, 0.0))
        wastage_values.append(waste_map.get(day, 0.0))

    return labels, consumption_values, wastage_values
