from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from inventory.models import (
    ChefBulletin,
    Recipe,
    RecipeItem,
    SaleTransaction,
    TrialRecipeVersion,
)
from inventory.services.chef_bulletins_service import (
    apply_chef_decision,
    refresh_chef_bulletins,
)

pytestmark = pytest.mark.django_db


def _make_recipe(item, *, name: str) -> Recipe:
    recipe = Recipe.objects.create(
        name=name,
        is_active=True,
        type=Recipe.Type.FINAL,
        selling_price=Decimal("100.00"),
        target_food_cost_pct=Decimal("30.00"),
    )
    RecipeItem.objects.create(
        recipe=recipe,
        item=item,
        quantity=Decimal("1000.00"),
        unit="GM",
        loss_pct=Decimal("0.00"),
    )
    return recipe


def test_refresh_chef_bulletins_creates_rule_based_alerts(item_factory):
    item = item_factory(
        name="Bulletin Chicken",
        unit_id=19,
        initial_purchase_price=Decimal("50.00"),
        last_purchase_price=Decimal("70.00"),
    )
    recipe = _make_recipe(item, name="Bulletin Chicken Curry")
    SaleTransaction.objects.create(
        recipe=recipe,
        quantity=Decimal("180.00"),
        net_sales=Decimal("18000.00"),
        source=SaleTransaction.Source.MANUAL,
        sale_date=timezone.now(),
    )

    today = timezone.localdate()
    refresh_chef_bulletins(today, today)

    alerts = set(
        ChefBulletin.objects.filter(recipe=recipe, period_start=today, period_end=today)
        .values_list("alert_type", flat=True)
    )
    assert ChefBulletin.AlertType.FOOD_COST_ABOVE_TARGET in alerts
    assert ChefBulletin.AlertType.HIGH_SALES_LOW_MARGIN in alerts
    assert ChefBulletin.AlertType.INGREDIENT_PRICE_INCREASED in alerts
    assert ChefBulletin.AlertType.RECIPE_COST_CHANGED in alerts


def test_apply_chef_decision_approve_trial_creates_trial_recipe(item_factory):
    item = item_factory(
        name="Trial Paneer",
        unit_id=19,
        initial_purchase_price=Decimal("120.00"),
        last_purchase_price=Decimal("140.00"),
    )
    recipe = _make_recipe(item, name="Trial Paneer Tikka")
    bulletin = ChefBulletin.objects.create(
        recipe=recipe,
        period_start=timezone.localdate(),
        period_end=timezone.localdate(),
        alert_type=ChefBulletin.AlertType.FOOD_COST_ABOVE_TARGET,
        current_food_cost_pct=Decimal("45.00"),
        target_food_cost_pct=Decimal("30.00"),
        monthly_sales=Decimal("12000.00"),
        unrealised_profit=Decimal("1800.00"),
        expected_saving=Decimal("1800.00"),
        risk_level=ChefBulletin.RiskLevel.MEDIUM,
    )
    user_model = get_user_model()
    user = user_model.objects.create_user(username="chef_decider", password="pw")

    result = apply_chef_decision(
        bulletin=bulletin,
        decision=ChefBulletin.ChefDecision.APPROVE_TRIAL,
        user=user,
        notes="Run trial with alternate marinade.",
    )

    bulletin.refresh_from_db()
    assert bulletin.chef_decision == ChefBulletin.ChefDecision.APPROVE_TRIAL
    assert bulletin.is_open is False
    assert result.trial_version is not None
    trial_version = result.trial_version
    assert TrialRecipeVersion.objects.filter(pk=trial_version.pk).exists()
    assert trial_version.trial_recipe is not None
    assert trial_version.trial_recipe.is_active is False
    assert RecipeItem.objects.filter(recipe=trial_version.trial_recipe).count() == RecipeItem.objects.filter(
        recipe=recipe
    ).count()
