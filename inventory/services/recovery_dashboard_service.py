"""Owner-facing food-cost recovery dashboard calculations."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict

from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse

from inventory.models import SavingsLedger
from inventory.services import dashboard_kpis as dkpis

MONEY_PLACES = Decimal("0.01")
PCT_PLACES = Decimal("0.1")
ZERO_MONEY = Decimal("0.00")


def _as_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _bundle_value(bundle: Dict[str, Any], key: str, fallback):
    if key in bundle:
        return bundle[key]
    return fallback()


def _money(value: Any) -> Decimal:
    return _as_decimal(value).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def _positive_money(value: Any) -> Decimal:
    return max(_money(value), ZERO_MONEY)


def _pct(value: Any) -> Decimal | None:
    if value is None:
        return None
    return _as_decimal(value).quantize(PCT_PLACES, rounding=ROUND_HALF_UP)


def _food_cost_gap(
    current_food_cost_pct: Decimal | None,
    target_food_cost_pct: Decimal | None,
) -> Decimal | None:
    if current_food_cost_pct is None or target_food_cost_pct is None:
        return None
    return (current_food_cost_pct - target_food_cost_pct).quantize(
        PCT_PLACES, rounding=ROUND_HALF_UP
    )


def _leakage_areas(
    *,
    food_cost_gap_pct: Decimal | None,
    unrealised_profit: Decimal,
    wastage: Decimal,
) -> list[dict[str, Any]]:
    areas: list[dict[str, Any]] = []
    if food_cost_gap_pct is not None and food_cost_gap_pct > 0:
        areas.append(
            {
                "label": "Food cost above target",
                "amount": unrealised_profit,
                "detail": f"{food_cost_gap_pct}% gap vs target",
                "url": reverse("food_cost_report"),
                "status": "danger",
            }
        )
    if wastage > 0:
        areas.append(
            {
                "label": "Recorded wastage",
                "amount": wastage,
                "detail": "Stock marked as wastage in this period",
                "url": reverse("stock_movements") + "?section=waste",
                "status": "warning",
            }
        )
    if not areas:
        areas.append(
            {
                "label": "No material leakage detected",
                "amount": ZERO_MONEY,
                "detail": "Keep reviewing purchases, recipes, and wastage weekly",
                "url": reverse("food_cost_report"),
                "status": "success",
            }
        )
    return areas[:3]


def _weekly_action_plan(
    *,
    food_cost_gap_pct: Decimal | None,
    target_food_cost_pct: Decimal | None,
    wastage: Decimal,
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    if target_food_cost_pct is None:
        actions.append(
            {
                "title": "Set target food cost percentages",
                "detail": "Add targets to active menu recipes before reviewing leakage.",
                "url": reverse("food_cost_report"),
            }
        )
    elif food_cost_gap_pct is not None and food_cost_gap_pct > 0:
        actions.append(
            {
                "title": "Review recipes above target",
                "detail": "Prioritise recipes with the widest food-cost gap.",
                "url": reverse("food_cost_report"),
            }
        )
    else:
        actions.append(
            {
                "title": "Keep target controls active",
                "detail": "Review recipe costs weekly to catch price changes early.",
                "url": reverse("food_cost_report"),
            }
        )

    actions.append(
        {
            "title": "Check purchase prices before ordering",
            "detail": "Use last purchase price as the baseline until vendor comparison is added.",
            "url": reverse("purchase_orders_list"),
        }
    )
    if wastage > 0:
        actions.append(
            {
                "title": "Reduce recorded wastage",
                "detail": "Review wastage reasons and assign one kitchen fix this week.",
                "url": reverse("stock_movements") + "?section=waste",
            }
        )
    else:
        actions.append(
            {
                "title": "Record wastage consistently",
                "detail": "Use the wastage form so leakage can be separated from variance.",
                "url": reverse("stock_movements") + "?section=waste",
            }
        )
    return actions


def _recovered_profit_this_month(end_date) -> Decimal:
    total = SavingsLedger.objects.filter(
        date__year=end_date.year,
        date__month=end_date.month,
        status__in=[
            SavingsLedger.Status.CONFIRMED,
            SavingsLedger.Status.VERIFIED,
        ],
    ).aggregate(
        total=Coalesce(
            Sum("confirmed_saving"),
            Decimal("0"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["total"]
    return _money(total or ZERO_MONEY)


def build_owner_money_dashboard(
    start,
    end,
    bundle: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return Phase 1 owner dashboard money metrics.

    Phase 1 has no savings ledger yet, so recovered profit is a zero placeholder.
    Phase 2 should replace it with confirmed and verified ledger totals.
    """
    bundle = bundle or {}
    opening_stock = _money(
        _bundle_value(
            bundle, "opening_stock", lambda: dkpis.opening_stock_value(start, end)
        )
    )
    purchases = _money(
        _bundle_value(bundle, "purchases", lambda: dkpis.purchases_total(start, end))
    )
    closing_stock = _money(
        _bundle_value(bundle, "closing_stock", dkpis.closing_stock_value)
    )
    actual_food_cost = _money(opening_stock + purchases - closing_stock)
    sales_revenue = _money(
        _bundle_value(bundle, "sales_revenue", lambda: dkpis.sales_revenue(start, end))
    )
    current_food_cost_pct = _pct(
        _bundle_value(
            bundle, "actual_fc", lambda: dkpis.actual_food_cost_pct(start, end)
        )
    )
    target_food_cost_pct = _pct(
        _bundle_value(bundle, "ideal_fc", lambda: dkpis.ideal_food_cost_pct(start, end))
    )
    food_cost_gap_pct = _food_cost_gap(current_food_cost_pct, target_food_cost_pct)
    positive_gap_pct = max(food_cost_gap_pct or Decimal("0"), Decimal("0"))
    unrealised_profit = _positive_money(
        sales_revenue * positive_gap_pct / Decimal("100")
    )
    recovered_profit_this_month = _recovered_profit_this_month(end)
    remaining_opportunity = _positive_money(
        unrealised_profit - recovered_profit_this_month
    )
    wastage = _money(
        _bundle_value(bundle, "wastage", lambda: dkpis.wastage_total(start, end))
    )

    return {
        "opening_stock": opening_stock,
        "purchases": purchases,
        "closing_stock": closing_stock,
        "actual_food_cost": actual_food_cost,
        "sales_revenue": sales_revenue,
        "current_food_cost_pct": current_food_cost_pct,
        "target_food_cost_pct": target_food_cost_pct,
        "food_cost_gap_pct": food_cost_gap_pct,
        "unrealised_profit": unrealised_profit,
        "recovered_profit_this_month": recovered_profit_this_month,
        "remaining_opportunity": remaining_opportunity,
        "wastage": wastage,
        "top_leakage_areas": _leakage_areas(
            food_cost_gap_pct=food_cost_gap_pct,
            unrealised_profit=unrealised_profit,
            wastage=wastage,
        ),
        "weekly_action_plan": _weekly_action_plan(
            food_cost_gap_pct=food_cost_gap_pct,
            target_food_cost_pct=target_food_cost_pct,
            wastage=wastage,
        ),
    }
