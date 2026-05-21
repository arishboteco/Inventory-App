from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from inventory.models import (
    ChefBulletin,
    Recipe,
    RecipeItem,
    SaleTransaction,
    TrialRecipeVersion,
)
from inventory.services.variance_service import build_variance_report

ZERO = Decimal("0")
HIGH_SALES_THRESHOLD = Decimal("10000")
LOW_MARGIN_THRESHOLD = Decimal("60")
MAX_PCT = Decimal("9999.99")
MAX_MONEY = Decimal("999999999999.99")


def _as_decimal(value) -> Decimal:
    if value in (None, ""):
        return ZERO
    return Decimal(str(value))


def _clamp_decimal(
    value: Decimal,
    *,
    min_value: Decimal = ZERO,
    max_value: Decimal,
    places: str = "0.01",
) -> Decimal:
    quant = Decimal(places)
    bounded = min(max(value, min_value), max_value)
    return bounded.quantize(quant)


def _month_window(ref_date: date | None = None) -> tuple[date, date]:
    end = ref_date or timezone.localdate()
    start = end - timedelta(days=29)
    return start, end


def _suggested_change(alert_type: str) -> str:
    suggestions = {
        ChefBulletin.AlertType.FOOD_COST_ABOVE_TARGET: (
            "Review ingredient yields and portion size. Start with top cost drivers."
        ),
        ChefBulletin.AlertType.INGREDIENT_PRICE_INCREASED: (
            "Renegotiate pricing or approve an alternate vendor for high-impact ingredients."
        ),
        ChefBulletin.AlertType.RECIPE_COST_CHANGED: (
            "Recheck the recipe card and validate latest ingredient prices."
        ),
        ChefBulletin.AlertType.HIGH_SALES_LOW_MARGIN: (
            "Run a trial version with lower-cost swaps while protecting guest experience."
        ),
        ChefBulletin.AlertType.ACTUAL_USAGE_ABOVE_IDEAL: (
            "Audit prep loss and wastage for linked ingredients this week."
        ),
    }
    return suggestions.get(alert_type, "Review this recipe with the kitchen team.")


def _headline(alert_type: str, recipe_name: str) -> str:
    labels = {
        ChefBulletin.AlertType.FOOD_COST_ABOVE_TARGET: "Food cost above target",
        ChefBulletin.AlertType.INGREDIENT_PRICE_INCREASED: "Ingredient price increased",
        ChefBulletin.AlertType.RECIPE_COST_CHANGED: "Recipe cost changed",
        ChefBulletin.AlertType.HIGH_SALES_LOW_MARGIN: "High sales but low margin",
        ChefBulletin.AlertType.ACTUAL_USAGE_ABOVE_IDEAL: "Actual usage above ideal",
    }
    return f"{labels.get(alert_type, 'Recipe alert')}: {recipe_name}"


def _risk_level(expected_saving: Decimal, gap_pct: Decimal) -> str:
    if expected_saving >= Decimal("10000") or gap_pct >= Decimal("10"):
        return ChefBulletin.RiskLevel.HIGH
    if expected_saving >= Decimal("3000") or gap_pct >= Decimal("4"):
        return ChefBulletin.RiskLevel.MEDIUM
    return ChefBulletin.RiskLevel.LOW


def _recipe_cost_drivers(recipe: Recipe) -> list[str]:
    drivers: list[tuple[Decimal, str]] = []
    for row in recipe.items.select_related("item", "sub_recipe").all():
        line_cost = _as_decimal(row.get_line_cost())
        if line_cost <= 0:
            continue
        if row.item_id:
            label = row.item.name
        elif row.sub_recipe_id:
            label = f"[Sub] {row.sub_recipe.name}"
        else:
            continue
        drivers.append((line_cost, label))
    drivers.sort(key=lambda entry: entry[0], reverse=True)
    return [name for _, name in drivers[:3]]


def _sales_by_recipe(start_date: date, end_date: date) -> dict[int, dict[str, Decimal]]:
    sales_rows = (
        SaleTransaction.objects.filter(
            sale_date__date__gte=start_date,
            sale_date__date__lte=end_date,
            recipe__isnull=False,
        )
        .values("recipe_id")
        .annotate(
            qty_total=Coalesce(Sum("quantity"), ZERO, output_field=DecimalField()),
            net_total=Coalesce(
                Sum("net_sales"),
                ZERO,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            gross_total=Coalesce(
                Sum("gross_sales"),
                ZERO,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
    )
    result: dict[int, dict[str, Decimal]] = {}
    for row in sales_rows:
        recipe_id = row.get("recipe_id")
        if recipe_id is None:
            continue
        net_total = _as_decimal(row.get("net_total"))
        gross_total = _as_decimal(row.get("gross_total"))
        qty_total = _as_decimal(row.get("qty_total"))
        result[recipe_id] = {
            "qty_total": qty_total,
            "sales_total": net_total
            if net_total > 0
            else (gross_total if gross_total > 0 else ZERO),
        }
    return result


def _build_alert_payload(
    *,
    recipe: Recipe,
    alert_type: str,
    start_date: date,
    end_date: date,
    monthly_sales: Decimal,
    current_food_cost_pct: Decimal,
    target_food_cost_pct: Decimal,
    expected_saving: Decimal,
    unrealised_profit: Decimal,
    main_cost_drivers: list[str],
) -> dict:
    gap_pct = max(current_food_cost_pct - target_food_cost_pct, ZERO)
    return {
        "period_start": start_date,
        "period_end": end_date,
        "headline": _headline(alert_type, recipe.name),
        "current_food_cost_pct": current_food_cost_pct,
        "target_food_cost_pct": target_food_cost_pct,
        "monthly_sales": monthly_sales,
        "unrealised_profit": unrealised_profit,
        "main_cost_drivers": main_cost_drivers,
        "suggested_change": _suggested_change(alert_type),
        "expected_saving": expected_saving,
        "risk_level": _risk_level(expected_saving, gap_pct),
    }


def refresh_chef_bulletins(
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ChefBulletin]:
    if start_date is None or end_date is None:
        start_date, end_date = _month_window(end_date)
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    sales_map = _sales_by_recipe(start_date, end_date)
    variance = build_variance_report(start_date, end_date)
    unexplained_by_item: dict[int, Decimal] = {}
    for row in variance["rows"]:
        if row.unexplained_variance_value > 0:
            unexplained_by_item[row.item.pk] = _as_decimal(row.unexplained_variance_value)

    recipes = list(
        Recipe.objects.filter(type=Recipe.Type.FINAL, is_active=True)
        .prefetch_related("items__item", "items__sub_recipe")
        .order_by("name")
    )
    # Guard against legacy oversize decimal values that can break SQLite conversion.
    now = timezone.now()
    ChefBulletin.objects.filter(current_food_cost_pct__gt=MAX_PCT).update(
        current_food_cost_pct=MAX_PCT,
        updated_at=now,
    )
    ChefBulletin.objects.filter(target_food_cost_pct__gt=MAX_PCT).update(
        target_food_cost_pct=MAX_PCT,
        updated_at=now,
    )
    ChefBulletin.objects.filter(monthly_sales__gt=MAX_MONEY).update(
        monthly_sales=MAX_MONEY,
        updated_at=now,
    )
    ChefBulletin.objects.filter(unrealised_profit__gt=MAX_MONEY).update(
        unrealised_profit=MAX_MONEY,
        updated_at=now,
    )
    ChefBulletin.objects.filter(expected_saving__gt=MAX_MONEY).update(
        expected_saving=MAX_MONEY,
        updated_at=now,
    )

    existing_open = {
        (row["recipe_id"], row["alert_type"]): row["bulletin_id"]
        for row in ChefBulletin.objects.filter(
            is_open=True,
            period_start=start_date,
            period_end=end_date,
        ).values("bulletin_id", "recipe_id", "alert_type")
    }
    active_keys: set[tuple[int, str]] = set()

    for recipe in recipes:
        total_cost = _as_decimal(recipe.get_total_cost())
        current_pct_raw = recipe.compute_food_cost_percentage(total_cost=total_cost)
        current_pct = _clamp_decimal(
            _as_decimal(current_pct_raw),
            max_value=MAX_PCT,
            places="0.01",
        )
        target_pct = _clamp_decimal(
            _as_decimal(recipe.target_food_cost_pct or Decimal("30")),
            max_value=MAX_PCT,
            places="0.01",
        )
        sales_state = sales_map.get(recipe.pk) or {}
        monthly_sales = _clamp_decimal(
            _as_decimal(sales_state.get("sales_total")),
            max_value=MAX_MONEY,
            places="0.01",
        )
        sales_qty = _as_decimal(sales_state.get("qty_total"))
        expected_gap_pct = max(current_pct - target_pct, ZERO)
        unrealised_profit = _clamp_decimal(
            (monthly_sales * expected_gap_pct / Decimal("100")),
            max_value=MAX_MONEY,
            places="0.01",
        )
        main_cost_drivers = _recipe_cost_drivers(recipe)
        recipe_item_ids = set(
            RecipeItem.objects.filter(recipe=recipe, item__isnull=False).values_list(
                "item_id", flat=True
            )
        )

        alert_payloads: list[tuple[str, dict]] = []
        if current_pct > target_pct:
            alert_payloads.append(
                (
                    ChefBulletin.AlertType.FOOD_COST_ABOVE_TARGET,
                    _build_alert_payload(
                        recipe=recipe,
                        alert_type=ChefBulletin.AlertType.FOOD_COST_ABOVE_TARGET,
                        start_date=start_date,
                        end_date=end_date,
                        monthly_sales=monthly_sales,
                        current_food_cost_pct=current_pct,
                        target_food_cost_pct=target_pct,
                        expected_saving=unrealised_profit,
                        unrealised_profit=unrealised_profit,
                        main_cost_drivers=main_cost_drivers,
                    ),
                )
            )

        has_price_increase = False
        has_cost_change = False
        for row in recipe.items.select_related("item").all():
            item = row.item
            if not item:
                continue
            current_price = _as_decimal(item.last_purchase_price)
            initial_price = _as_decimal(item.initial_purchase_price)
            if initial_price > 0 and current_price > initial_price:
                has_price_increase = True
            if initial_price > 0 and current_price != initial_price:
                has_cost_change = True

        if has_price_increase:
            alert_payloads.append(
                (
                    ChefBulletin.AlertType.INGREDIENT_PRICE_INCREASED,
                    _build_alert_payload(
                        recipe=recipe,
                        alert_type=ChefBulletin.AlertType.INGREDIENT_PRICE_INCREASED,
                        start_date=start_date,
                        end_date=end_date,
                        monthly_sales=monthly_sales,
                        current_food_cost_pct=current_pct,
                        target_food_cost_pct=target_pct,
                        expected_saving=unrealised_profit,
                        unrealised_profit=unrealised_profit,
                        main_cost_drivers=main_cost_drivers,
                    ),
                )
            )

        if has_cost_change:
            alert_payloads.append(
                (
                    ChefBulletin.AlertType.RECIPE_COST_CHANGED,
                    _build_alert_payload(
                        recipe=recipe,
                        alert_type=ChefBulletin.AlertType.RECIPE_COST_CHANGED,
                        start_date=start_date,
                        end_date=end_date,
                        monthly_sales=monthly_sales,
                        current_food_cost_pct=current_pct,
                        target_food_cost_pct=target_pct,
                        expected_saving=unrealised_profit,
                        unrealised_profit=unrealised_profit,
                        main_cost_drivers=main_cost_drivers,
                    ),
                )
            )

        gross_margin_pct = Decimal("100") - current_pct
        if monthly_sales >= HIGH_SALES_THRESHOLD and gross_margin_pct < LOW_MARGIN_THRESHOLD:
            alert_payloads.append(
                (
                    ChefBulletin.AlertType.HIGH_SALES_LOW_MARGIN,
                    _build_alert_payload(
                        recipe=recipe,
                        alert_type=ChefBulletin.AlertType.HIGH_SALES_LOW_MARGIN,
                        start_date=start_date,
                        end_date=end_date,
                        monthly_sales=monthly_sales,
                        current_food_cost_pct=current_pct,
                        target_food_cost_pct=target_pct,
                        expected_saving=unrealised_profit,
                        unrealised_profit=unrealised_profit,
                        main_cost_drivers=main_cost_drivers,
                    ),
                )
            )

        unexplained_total = sum(
            (_as_decimal(unexplained_by_item.get(item_id)) for item_id in recipe_item_ids),
            ZERO,
        )
        unexplained_value = _clamp_decimal(
            _as_decimal(unexplained_total),
            max_value=MAX_MONEY,
            places="0.01",
        )
        if sales_qty > 0 and unexplained_value > 0:
            alert_payloads.append(
                (
                    ChefBulletin.AlertType.ACTUAL_USAGE_ABOVE_IDEAL,
                    _build_alert_payload(
                        recipe=recipe,
                        alert_type=ChefBulletin.AlertType.ACTUAL_USAGE_ABOVE_IDEAL,
                        start_date=start_date,
                        end_date=end_date,
                        monthly_sales=monthly_sales,
                        current_food_cost_pct=current_pct,
                        target_food_cost_pct=target_pct,
                        expected_saving=unexplained_value,
                        unrealised_profit=unrealised_profit,
                        main_cost_drivers=main_cost_drivers,
                    ),
                )
            )

        for alert_type, payload in alert_payloads:
            key = (recipe.pk, alert_type)
            active_keys.add(key)
            bulletin_id = existing_open.get(key)
            if bulletin_id is None:
                ChefBulletin.objects.create(
                    recipe=recipe,
                    alert_type=alert_type,
                    **payload,
                )
                continue
            ChefBulletin.objects.filter(pk=bulletin_id).update(
                **payload,
                updated_at=timezone.now(),
            )

    stale_ids = list(
        ChefBulletin.objects.filter(
            is_open=True,
            period_start=start_date,
            period_end=end_date,
        ).values_list("bulletin_id", "recipe_id", "alert_type")
    )
    for bulletin_id, recipe_id, alert_type in stale_ids:
        if (recipe_id, alert_type) not in active_keys:
            ChefBulletin.objects.filter(pk=bulletin_id).update(
                is_open=False,
                updated_at=timezone.now(),
            )

    return list(
        ChefBulletin.objects.filter(
            period_start=start_date,
            period_end=end_date,
        ).values_list("bulletin_id", flat=True)
    )


@dataclass
class BulletinDecisionResult:
    bulletin: ChefBulletin
    trial_version: TrialRecipeVersion | None


def _next_trial_recipe_name(source_recipe: Recipe) -> str:
    suffix = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"{source_recipe.name} (Trial {suffix})"


def _clone_trial_recipe(
    *,
    bulletin: ChefBulletin,
    user,
    notes: str,
) -> TrialRecipeVersion:
    existing = (
        TrialRecipeVersion.objects.filter(bulletin=bulletin)
        .select_related("trial_recipe")
        .first()
    )
    if existing:
        return existing

    source = bulletin.recipe
    trial_recipe = Recipe.objects.create(
        name=_next_trial_recipe_name(source),
        description=source.description,
        is_active=False,
        type=source.type,
        default_yield_qty=source.default_yield_qty,
        default_yield_unit=source.default_yield_unit,
        plating_notes=source.plating_notes,
        tags=source.tags,
        version=(source.version or 1) + 1,
        selling_price=source.selling_price,
        target_food_cost_pct=source.target_food_cost_pct,
    )
    source_rows = RecipeItem.objects.filter(recipe=source).order_by("sort_order", "pk")
    for row in source_rows:
        RecipeItem.objects.create(
            recipe=trial_recipe,
            item=row.item,
            sub_recipe=row.sub_recipe,
            quantity=row.quantity,
            unit=row.unit,
            loss_pct=row.loss_pct,
            sort_order=row.sort_order,
            notes=row.notes,
        )

    return TrialRecipeVersion.objects.create(
        bulletin=bulletin,
        source_recipe=source,
        trial_recipe=trial_recipe,
        status=TrialRecipeVersion.Status.DRAFT,
        notes=notes or "Trial recipe generated from chef bulletin.",
        created_by=user if user and user.is_authenticated else None,
    )


def apply_chef_decision(
    *,
    bulletin: ChefBulletin,
    decision: str,
    user,
    notes: str = "",
) -> BulletinDecisionResult:
    decision = (decision or "").strip().upper()
    valid_decisions = {choice[0] for choice in ChefBulletin.ChefDecision.choices}
    if decision not in valid_decisions:
        raise ValueError("Invalid chef decision.")

    trial_version: TrialRecipeVersion | None = None
    bulletin.chef_decision = decision
    bulletin.decision_notes = notes or ""
    bulletin.decided_at = timezone.now()
    bulletin.decided_by = user if user and user.is_authenticated else None

    if decision == ChefBulletin.ChefDecision.APPROVE_TRIAL:
        trial_version = _clone_trial_recipe(bulletin=bulletin, user=user, notes=notes)
        bulletin.is_open = False
    elif decision in {
        ChefBulletin.ChefDecision.REJECT,
        ChefBulletin.ChefDecision.SEND_TO_OWNER,
    }:
        bulletin.is_open = False
    else:
        bulletin.is_open = True

    bulletin.save()
    return BulletinDecisionResult(bulletin=bulletin, trial_version=trial_version)
