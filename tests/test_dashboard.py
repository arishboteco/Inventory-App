import json
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone

from core.viewmodels import DashboardContext
from inventory.models import (
    Recipe,
    RecipeItem,
    SaleTransaction,
    SavingsLedger,
    StockTransaction,
)
from inventory.services import dashboard_kpis as dkpis


@pytest.mark.django_db
def test_dashboard_context_basic():
    ctx = DashboardContext(labels=["2024-01-01"], values=[1])
    data = ctx.as_dict()
    assert data["trend_labels"] == json.dumps(["2024-01-01"])
    assert data["trend_values"] == json.dumps([1])
    assert data["list_title"] == "Dashboard"
    assert "items" not in data and "suppliers" not in data


@pytest.mark.django_db
def test_dashboard_low_stock(client, item_factory, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="pw")
    perm = Permission.objects.get(codename="add_purchaseorder")
    user.user_permissions.add(perm)
    client.force_login(user)
    item_factory(name="Foo", reorder_point=10, current_stock=5)
    item_factory(name="Inactive", reorder_point=10, current_stock=5, is_active=False)
    resp = client.get(reverse("root"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_dashboard_kpis_endpoint(client, item_factory):
    fresh = item_factory(name="Foo", reorder_point=10, current_stock=5)
    StockTransaction.objects.create(
        item=fresh,
        quantity_change=1,
        transaction_type="RECEIVING",
        transaction_date=timezone.now(),
    )

    resp = client.get(reverse("dashboard-kpis"))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Consumption breakdown" in html


@pytest.mark.django_db
def test_actual_food_cost_uses_stock_formula_not_only_sale_issue(item_factory):
    end = timezone.now().date()
    start = end
    item = item_factory(
        name="Chicken",
        current_stock=Decimal("14.00"),
        last_purchase_price=Decimal("10.00"),
    )
    recipe = Recipe.objects.create(
        name="Chicken Plate",
        is_active=True,
        type=Recipe.Type.FINAL,
        selling_price=Decimal("100.00"),
        target_food_cost_pct=Decimal("5.00"),
    )
    SaleTransaction.objects.create(recipe=recipe, quantity=Decimal("1.00"))
    StockTransaction.objects.create(
        item=item,
        quantity_change=Decimal("5.00"),
        transaction_type="RECEIVING",
        transaction_date=timezone.now(),
    )
    StockTransaction.objects.create(
        item=item,
        quantity_change=Decimal("-1.00"),
        transaction_type="WASTAGE",
        transaction_date=timezone.now(),
    )

    assert dkpis.actual_food_cost_pct(start, end) == 10.0


@pytest.mark.django_db
def test_dashboard_renders_owner_money_recovery_cards(client, django_user_model):
    user = django_user_model.objects.create_user(username="owner", password="pw")
    client.force_login(user)

    resp = client.get(reverse("root"))

    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Food-cost recovery system" in html
    assert "Current Food Cost %" in html
    assert "Target Food Cost %" in html
    assert "Food Cost Gap" in html
    assert "Unrealised Profit" in html
    assert "Recovered Profit This Month" in html
    assert "Remaining Opportunity" in html
    assert "Top leakage areas" in html
    assert "Weekly action plan" in html


@pytest.mark.django_db
def test_dashboard_renders_chart_and_kpis(client, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="pw")
    client.force_login(user)
    resp = client.get(reverse("root"))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Consumption vs Wastage" in html
    assert "Consumption breakdown" in html
    assert "Top movers" in html


@pytest.mark.django_db
def test_dashboard_recovered_profit_uses_confirmed_and_verified_ledger_entries(
    client, django_user_model
):
    user = django_user_model.objects.create_user(username="owner2", password="pw")
    client.force_login(user)

    today = timezone.now().date()
    SavingsLedger.objects.create(
        date=today,
        saving_type=SavingsLedger.SavingType.VENDOR_SAVING,
        status=SavingsLedger.Status.CONFIRMED,
        confirmed_saving=Decimal("1200.00"),
    )
    SavingsLedger.objects.create(
        date=today,
        saving_type=SavingsLedger.SavingType.WASTE_REDUCTION,
        status=SavingsLedger.Status.VERIFIED,
        confirmed_saving=Decimal("800.00"),
    )
    SavingsLedger.objects.create(
        date=today,
        saving_type=SavingsLedger.SavingType.RECIPE_OPTIMISATION,
        status=SavingsLedger.Status.ESTIMATED,
        confirmed_saving=Decimal("9999.00"),
    )

    resp = client.get(reverse("root"))
    assert resp.status_code == 200
    assert resp.context["recovered_profit_this_month"] == Decimal("2000.00")


@pytest.mark.django_db
def test_dashboard_surfaces_unexplained_variance_area(
    client, django_user_model, item_factory
):
    user = django_user_model.objects.create_user(username="owner3", password="pw")
    client.force_login(user)
    item = item_factory(
        name="Unexplained Variance Item",
        unit_id=19,
        current_stock=Decimal("10.00"),
        last_purchase_price=Decimal("200.00"),
    )
    recipe = Recipe.objects.create(
        name="Unexplained Recipe",
        is_active=True,
        type=Recipe.Type.FINAL,
        selling_price=Decimal("300.00"),
        target_food_cost_pct=Decimal("30.00"),
    )
    RecipeItem.objects.create(
        recipe=recipe,
        item=item,
        quantity=Decimal("100.00"),
        unit="GM",
        loss_pct=Decimal("0.00"),
    )
    SaleTransaction.objects.create(
        recipe=recipe,
        quantity=Decimal("5.00"),
        sale_date=timezone.now(),
    )
    StockTransaction.objects.create(
        item=item,
        quantity_change=Decimal("1.00"),
        transaction_type="RECEIVING",
        transaction_date=timezone.now(),
    )
    StockTransaction.objects.create(
        item=item,
        quantity_change=Decimal("-1.50"),
        transaction_type="ISSUE",
        transaction_date=timezone.now(),
    )

    resp = client.get(reverse("root"))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Unexplained variance" in html
