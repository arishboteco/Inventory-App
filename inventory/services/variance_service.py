from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum

from inventory.models import Item, RecipeItem, SaleTransaction, StockTransaction
from inventory.services.units_service import UnitsService

ZERO = Decimal("0")


def _as_decimal(value) -> Decimal:
    if value in (None, ""):
        return ZERO
    return Decimal(str(value))


def _to_base_qty(item: Item, purchase_qty: Decimal) -> Decimal:
    factor = _as_decimal(getattr(item.unit, "conversion_factor", None))
    if factor <= 0:
        factor = Decimal("1")
    return purchase_qty * factor


def _from_base_qty(item: Item, base_qty: Decimal) -> Decimal:
    factor = _as_decimal(getattr(item.unit, "conversion_factor", None))
    if factor <= 0:
        factor = Decimal("1")
    try:
        return base_qty / factor
    except (ArithmeticError, ZeroDivisionError):
        return ZERO


def _effective_item_qty(qty: Decimal, loss_pct: Decimal) -> Decimal:
    if qty <= 0 or loss_pct <= 0 or loss_pct >= 100:
        return qty
    try:
        return qty / (Decimal("1") - (loss_pct / Decimal("100")))
    except (ArithmeticError, ZeroDivisionError):
        return qty


def _effective_subrecipe_qty(qty: Decimal, loss_pct: Decimal) -> Decimal:
    if qty <= 0 or loss_pct <= 0:
        return qty
    return qty * (Decimal("1") + (loss_pct / Decimal("100")))


def _recipe_lines_with_subrecipes(root_recipe_ids: set[int]) -> dict[int, list[RecipeItem]]:
    line_map: dict[int, list[RecipeItem]] = {}
    visited: set[int] = set()
    queue = set(root_recipe_ids)

    while queue:
        batch = queue - visited
        if not batch:
            break
        visited.update(batch)
        rows = list(
            RecipeItem.objects.filter(recipe_id__in=batch)
            .select_related("item__unit", "sub_recipe")
            .order_by("recipe_id", "sort_order", "pk")
        )
        for row in rows:
            line_map.setdefault(row.recipe_id, []).append(row)
            if row.sub_recipe_id and row.sub_recipe_id not in visited:
                queue.add(row.sub_recipe_id)
    return line_map


def _expand_recipe_usage(
    recipe_id: int,
    multiplier: Decimal,
    line_map: dict[int, list[RecipeItem]],
    output: dict[int, Decimal],
    stack: set[int],
) -> None:
    if multiplier <= 0 or recipe_id in stack:
        return
    stack_next = set(stack)
    stack_next.add(recipe_id)

    for line in line_map.get(recipe_id, []):
        qty = _as_decimal(line.quantity)
        loss_pct = _as_decimal(line.loss_pct)
        if line.item_id:
            per_sale_qty = _effective_item_qty(qty, loss_pct)
            if per_sale_qty > 0:
                output[line.item_id] += per_sale_qty * multiplier
            continue
        if line.sub_recipe_id:
            sub_qty = _effective_subrecipe_qty(qty, loss_pct)
            _expand_recipe_usage(
                line.sub_recipe_id,
                sub_qty * multiplier,
                line_map,
                output,
                stack_next,
            )


def _ideal_usage_by_item(start_date: date, end_date: date):
    sales_rows = (
        SaleTransaction.objects.filter(
            sale_date__date__gte=start_date,
            sale_date__date__lte=end_date,
            recipe__isnull=False,
        )
        .values("recipe_id")
        .annotate(total_qty=Sum("quantity"))
    )
    sales_by_recipe = {
        row["recipe_id"]: _as_decimal(row["total_qty"])
        for row in sales_rows
        if row["recipe_id"] is not None
    }
    if not sales_by_recipe:
        return {}, 0

    line_map = _recipe_lines_with_subrecipes(set(sales_by_recipe.keys()))
    ideal_by_item: dict[int, Decimal] = defaultdict(lambda: ZERO)
    for recipe_id, sale_qty in sales_by_recipe.items():
        _expand_recipe_usage(recipe_id, sale_qty, line_map, ideal_by_item, set())
    return ideal_by_item, len(sales_by_recipe)


def _actual_usage_by_item(start_date: date, end_date: date, candidate_item_ids: set[int]):
    if not candidate_item_ids:
        return {}
    items = {
        item.pk: item
        for item in Item.objects.filter(pk__in=candidate_item_ids).select_related("unit")
    }

    stock_rows = (
        StockTransaction.objects.filter(
            item_id__in=candidate_item_ids,
            transaction_date__date__gte=start_date,
            transaction_date__date__lte=end_date,
        )
        .values("item_id")
        .annotate(
            net_qty=Sum("quantity_change"),
            purchases_qty=Sum(
                "quantity_change",
                filter=Q(transaction_type="RECEIVING"),
            ),
            wastage_qty=Sum(
                "quantity_change",
                filter=Q(transaction_type="WASTAGE"),
            ),
        )
    )
    stock_map = {row["item_id"]: row for row in stock_rows}

    actual = {}
    for item_id, item in items.items():
        row = stock_map.get(item_id) or {}
        closing_pu = _as_decimal(item.current_stock)
        net_qty_pu = _as_decimal(row.get("net_qty"))
        purchases_pu = _as_decimal(row.get("purchases_qty"))
        wastage_pu = _as_decimal(row.get("wastage_qty"))
        opening_pu = closing_pu - net_qty_pu
        actual_pu = opening_pu + purchases_pu - closing_pu
        actual_base = _to_base_qty(item, actual_pu)
        wastage_base = abs(_to_base_qty(item, wastage_pu))
        actual[item_id] = {
            "item": item,
            "opening_base": _to_base_qty(item, opening_pu),
            "purchases_base": _to_base_qty(item, purchases_pu),
            "closing_base": _to_base_qty(item, closing_pu),
            "actual_base": actual_base,
            "wastage_base": wastage_base,
        }
    return actual


def _likely_reason_and_action(
    *,
    ideal_base: Decimal,
    actual_base: Decimal,
    variance_base: Decimal,
    recorded_wastage_base: Decimal,
    unexplained_base: Decimal,
) -> tuple[str, str]:
    if ideal_base == 0 and actual_base > 0:
        return (
            "Usage exists but mapped sales are missing for this item.",
            "Map missing POS menu items to recipes and verify recipe ingredients.",
        )
    if variance_base > 0 and recorded_wastage_base > 0 and unexplained_base <= 0:
        return (
            "Over-usage is fully explained by recorded wastage.",
            "Keep logging wastage reasons and reduce avoidable kitchen loss.",
        )
    if variance_base > 0 and recorded_wastage_base > 0 and unexplained_base > 0:
        return (
            "Recorded wastage explains part of over-usage.",
            "Reduce wastage first, then investigate remaining unexplained leakage.",
        )
    if variance_base > 0:
        return (
            "Actual usage is above ideal usage.",
            "Recheck portioning, receiving quality, and unrecorded waste for this item.",
        )
    if variance_base < 0:
        return (
            "Actual usage is below ideal usage.",
            "Validate recipe quantities and sales mapping for this item.",
        )
    return (
        "Usage is aligned with ideal.",
        "Keep monitoring this item weekly.",
    )


@dataclass
class VarianceRow:
    item: Item
    unit_label: str
    ideal_usage: Decimal
    actual_usage: Decimal
    variance_qty: Decimal
    variance_value: Decimal
    recorded_wastage_qty: Decimal
    recorded_wastage_value: Decimal
    unexplained_variance_qty: Decimal
    unexplained_variance_value: Decimal
    likely_reason: str
    recommended_action: str
    is_unmapped_candidate: bool


def build_variance_report(start_date: date, end_date: date) -> dict:
    ideal_map, mapped_recipe_count = _ideal_usage_by_item(start_date, end_date)
    period_item_ids = set(
        StockTransaction.objects.filter(
            transaction_date__date__gte=start_date,
            transaction_date__date__lte=end_date,
            item__isnull=False,
        ).values_list("item_id", flat=True)
    )
    candidate_item_ids = set(ideal_map.keys()) | period_item_ids
    actual_map = _actual_usage_by_item(start_date, end_date, candidate_item_ids)

    rows: list[VarianceRow] = []
    total_positive_leakage = ZERO
    total_negative_variance_value = ZERO
    total_recorded_wastage_value = ZERO
    total_unexplained_leakage_value = ZERO

    item_lookup = {
        item.pk: item
        for item in Item.objects.filter(pk__in=(set(ideal_map.keys()) | set(actual_map.keys()))).select_related(
            "unit"
        )
    }
    for item in sorted(item_lookup.values(), key=lambda row: (row.name or "").lower()):
        item_id = item.pk
        state = actual_map.get(item_id)
        if item is None:
            continue

        ideal_base = _as_decimal(ideal_map.get(item_id))
        actual_base = _as_decimal(state["actual_base"] if state else ZERO)
        variance_base = actual_base - ideal_base
        cost_per_base = UnitsService.cost_per_base_for_item(item)
        variance_value = variance_base * _as_decimal(cost_per_base)
        recorded_wastage_base = _as_decimal(state["wastage_base"] if state else ZERO)
        positive_variance_base = max(variance_base, ZERO)
        unexplained_base = max(positive_variance_base - recorded_wastage_base, ZERO)
        recorded_wastage_value = recorded_wastage_base * _as_decimal(cost_per_base)
        unexplained_value = unexplained_base * _as_decimal(cost_per_base)
        likely_reason, action = _likely_reason_and_action(
            ideal_base=ideal_base,
            actual_base=actual_base,
            variance_base=variance_base,
            recorded_wastage_base=recorded_wastage_base,
            unexplained_base=unexplained_base,
        )
        is_unmapped_candidate = ideal_base == 0 and actual_base > 0

        if variance_value > 0:
            total_positive_leakage += variance_value
        elif variance_value < 0:
            total_negative_variance_value += abs(variance_value)
        total_recorded_wastage_value += recorded_wastage_value
        total_unexplained_leakage_value += unexplained_value

        rows.append(
            VarianceRow(
                item=item,
                unit_label=getattr(item.unit, "purchase_unit", "unit"),
                ideal_usage=_from_base_qty(item, ideal_base),
                actual_usage=_from_base_qty(item, actual_base),
                variance_qty=_from_base_qty(item, variance_base),
                variance_value=variance_value,
                recorded_wastage_qty=_from_base_qty(item, recorded_wastage_base),
                recorded_wastage_value=recorded_wastage_value,
                unexplained_variance_qty=_from_base_qty(item, unexplained_base),
                unexplained_variance_value=unexplained_value,
                likely_reason=likely_reason,
                recommended_action=action,
                is_unmapped_candidate=is_unmapped_candidate,
            )
        )

    rows.sort(key=lambda row: row.variance_value, reverse=True)

    unmapped_sales = SaleTransaction.objects.filter(
        sale_date__date__gte=start_date,
        sale_date__date__lte=end_date,
        recipe__isnull=True,
    )
    unmapped_count = unmapped_sales.count()

    return {
        "rows": rows,
        "summary": {
            "total_items": len(rows),
            "mapped_recipe_count": mapped_recipe_count,
            "unmapped_sales_count": unmapped_count,
            "leakage_value": total_positive_leakage,
            "favourable_value": total_negative_variance_value,
            "recorded_wastage_value": total_recorded_wastage_value,
            "unexplained_leakage_value": total_unexplained_leakage_value,
        },
    }
