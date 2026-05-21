from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from inventory.models import ChefBulletin, Recipe, RecipeItem, SaleTransaction

pytestmark = pytest.mark.django_db


def _recipe_for_bulletin(item, *, name: str) -> Recipe:
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


def test_chef_bulletins_list_page_renders(client, item_factory):
    item = item_factory(
        name="Chef List Chicken",
        unit_id=19,
        initial_purchase_price=Decimal("50.00"),
        last_purchase_price=Decimal("70.00"),
    )
    recipe = _recipe_for_bulletin(item, name="Chef List Curry")
    SaleTransaction.objects.create(
        recipe=recipe,
        quantity=Decimal("100.00"),
        net_sales=Decimal("12000.00"),
        sale_date=timezone.now(),
    )
    today = timezone.localdate()

    response = client.get(
        reverse("chef_bulletins_list"),
        {
            "start_date": today.isoformat(),
            "end_date": today.isoformat(),
            "state": "all",
        },
    )

    assert response.status_code == 200
    html = response.content.decode()
    assert "Chef Bulletins" in html
    assert "Chef List Curry" in html


def test_chef_bulletin_detail_and_decision_updates_status(client, item_factory):
    item = item_factory(name="Chef Detail Paneer", unit_id=19)
    recipe = _recipe_for_bulletin(item, name="Chef Detail Dish")
    bulletin = ChefBulletin.objects.create(
        recipe=recipe,
        period_start=timezone.localdate(),
        period_end=timezone.localdate(),
        alert_type=ChefBulletin.AlertType.RECIPE_COST_CHANGED,
        current_food_cost_pct=Decimal("34.00"),
        target_food_cost_pct=Decimal("30.00"),
        monthly_sales=Decimal("5000.00"),
        expected_saving=Decimal("200.00"),
    )

    detail_response = client.get(
        reverse("chef_bulletin_detail", kwargs={"bulletin_id": bulletin.pk})
    )
    assert detail_response.status_code == 200
    assert "Chef Detail Dish" in detail_response.content.decode()

    post_response = client.post(
        reverse("chef_bulletin_decision", kwargs={"bulletin_id": bulletin.pk}),
        {
            "decision": ChefBulletin.ChefDecision.REJECT,
            "decision_notes": "Not feasible this cycle.",
        },
    )

    assert post_response.status_code == 302
    bulletin.refresh_from_db()
    assert bulletin.chef_decision == ChefBulletin.ChefDecision.REJECT
    assert bulletin.is_open is False
