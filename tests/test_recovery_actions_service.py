from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from inventory.models import (
    Recipe,
    RecipeItem,
    RecoveryAction,
    SaleTransaction,
    SavingsLedger,
)
from inventory.services.recovery_actions_service import (
    apply_recovery_action_status,
    refresh_recovery_actions,
    summarize_recovery_actions,
)

pytestmark = pytest.mark.django_db


def _create_recipe(name: str) -> Recipe:
    return Recipe.objects.create(
        name=name,
        is_active=True,
        type=Recipe.Type.FINAL,
        selling_price=Decimal("250.00"),
        target_food_cost_pct=Decimal("30.00"),
    )


def test_refresh_recovery_actions_creates_and_deduplicates_bulletin_actions(item_factory):
    today = date.today()
    item = item_factory(
        name="Recovery Action Ingredient",
        unit_id=19,
        initial_purchase_price=Decimal("50.00"),
        last_purchase_price=Decimal("80.00"),
    )
    recipe = _create_recipe("Recovery Chicken Curry")
    RecipeItem.objects.create(
        recipe=recipe,
        item=item,
        quantity=Decimal("1000.00"),
        unit="GM",
        loss_pct=Decimal("0.00"),
    )
    SaleTransaction.objects.create(
        recipe=recipe,
        quantity=Decimal("50.00"),
        net_sales=Decimal("10000.00"),
        sale_date=timezone.now(),
    )
    first = refresh_recovery_actions(today, today)
    second = refresh_recovery_actions(today, today)

    assert first["created_from_bulletins"] >= 1
    assert second["created_from_bulletins"] == 0
    actions = RecoveryAction.objects.filter(linked_chef_bulletin__isnull=False)
    assert actions.exists()
    assert actions.filter(status=RecoveryAction.Status.SUGGESTED).exists()


def test_apply_recovery_action_status_verified_creates_and_links_ledger(item_factory):
    item = item_factory(name="Recovery Item")
    action = RecoveryAction.objects.create(
        title="Reduce wastage in prep",
        leakage_type=RecoveryAction.LeakageType.WASTE_REDUCTION,
        expected_saving=Decimal("450.00"),
        linked_item=item,
    )

    ledger = apply_recovery_action_status(
        action=action,
        status=RecoveryAction.Status.VERIFIED,
        verified_saving=Decimal("425.00"),
        notes="Verified in weekly review.",
    )

    action.refresh_from_db()
    assert action.status == RecoveryAction.Status.VERIFIED
    assert action.verified_saving == Decimal("425.00")
    assert ledger is not None
    assert ledger.status == SavingsLedger.Status.VERIFIED
    assert ledger.confirmed_saving == Decimal("425.00")
    assert ledger in action.linked_savings_entries.all()


def test_summarize_recovery_actions_rolls_up_expected_and_verified():
    RecoveryAction.objects.create(
        title="Action Suggested",
        leakage_type=RecoveryAction.LeakageType.FOOD_COST_GAP,
        expected_saving=Decimal("100.00"),
        status=RecoveryAction.Status.SUGGESTED,
    )
    RecoveryAction.objects.create(
        title="Action In Progress",
        leakage_type=RecoveryAction.LeakageType.VENDOR_PRICE,
        expected_saving=Decimal("250.00"),
        status=RecoveryAction.Status.IN_PROGRESS,
    )
    RecoveryAction.objects.create(
        title="Action Verified",
        leakage_type=RecoveryAction.LeakageType.WASTE_REDUCTION,
        expected_saving=Decimal("120.00"),
        verified_saving=Decimal("95.00"),
        status=RecoveryAction.Status.VERIFIED,
    )

    summary = summarize_recovery_actions()

    assert summary["open_opportunity"] == Decimal("350.00")
    assert summary["expected_recovery"] == Decimal("250.00")
    assert summary["verified_recovered_profit"] == Decimal("95.00")
