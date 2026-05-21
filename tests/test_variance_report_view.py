from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from inventory.models import Recipe, RecipeItem, SaleTransaction, StockTransaction

pytestmark = pytest.mark.django_db


def _create_recipe_with_item(name: str, item, ingredient_qty: Decimal):
    recipe = Recipe.objects.create(
        name=name,
        is_active=True,
        type=Recipe.Type.FINAL,
        selling_price=Decimal("250.00"),
        target_food_cost_pct=Decimal("30.00"),
    )
    RecipeItem.objects.create(
        recipe=recipe,
        item=item,
        quantity=ingredient_qty,
        unit="GM",
        loss_pct=Decimal("0.00"),
    )
    return recipe


def test_variance_report_page_renders(client, item_factory):
    item = item_factory(
        name="Variance Render Item",
        unit_id=19,
        current_stock=Decimal("9.00"),
        last_purchase_price=Decimal("180.00"),
    )
    recipe = _create_recipe_with_item("Variance Render Recipe", item, Decimal("100.00"))
    SaleTransaction.objects.create(
        recipe=recipe,
        quantity=Decimal("5.00"),
        sale_date=timezone.now(),
    )
    StockTransaction.objects.create(
        item=item,
        quantity_change=Decimal("-1.00"),
        transaction_type="ISSUE",
        transaction_date=timezone.now(),
    )

    response = client.get(reverse("variance_report"))

    assert response.status_code == 200
    html = response.content.decode()
    assert "Ideal vs Actual Variance" in html
    assert "Variance Render Item" in html
    assert "Recorded Wastage" in html
    assert "Unexplained" in html


def test_variance_report_show_mode_filters(client, item_factory):
    leak_item = item_factory(
        name="Leakage Chicken",
        unit_id=19,
        current_stock=Decimal("11.00"),
        last_purchase_price=Decimal("200.00"),
    )
    good_item = item_factory(
        name="Favourable Paneer",
        unit_id=19,
        current_stock=Decimal("3.50"),
        last_purchase_price=Decimal("120.00"),
    )
    unmapped_item = item_factory(
        name="Unmapped Mutton",
        unit_id=19,
        current_stock=Decimal("7.00"),
        last_purchase_price=Decimal("220.00"),
    )

    leak_recipe = _create_recipe_with_item("Leak Recipe", leak_item, Decimal("100.00"))
    good_recipe = _create_recipe_with_item("Good Recipe", good_item, Decimal("100.00"))

    SaleTransaction.objects.create(
        recipe=leak_recipe,
        quantity=Decimal("10.00"),
        sale_date=timezone.now(),
    )
    SaleTransaction.objects.create(
        recipe=good_recipe,
        quantity=Decimal("10.00"),
        sale_date=timezone.now(),
    )
    SaleTransaction.objects.create(
        recipe=None,
        pos_item_name="Unknown Mutton Curry",
        quantity=Decimal("3.00"),
        source=SaleTransaction.Source.POS_CSV,
        sale_date=timezone.now(),
    )

    StockTransaction.objects.create(
        item=leak_item,
        quantity_change=Decimal("3.00"),
        transaction_type="RECEIVING",
        transaction_date=timezone.now(),
    )
    StockTransaction.objects.create(
        item=leak_item,
        quantity_change=Decimal("-2.00"),
        transaction_type="ISSUE",
        transaction_date=timezone.now(),
    )
    StockTransaction.objects.create(
        item=good_item,
        quantity_change=Decimal("1.00"),
        transaction_type="RECEIVING",
        transaction_date=timezone.now(),
    )
    StockTransaction.objects.create(
        item=good_item,
        quantity_change=Decimal("-0.50"),
        transaction_type="ISSUE",
        transaction_date=timezone.now(),
    )
    StockTransaction.objects.create(
        item=unmapped_item,
        quantity_change=Decimal("-1.00"),
        transaction_type="ISSUE",
        transaction_date=timezone.now(),
    )

    leak_only = client.get(reverse("variance_report"), {"show": "leakage_only"})
    leak_html = leak_only.content.decode()
    assert leak_only.status_code == 200
    assert "Leakage Chicken" in leak_html
    assert "Favourable Paneer" not in leak_html

    unmapped_only = client.get(reverse("variance_report"), {"show": "unmapped_only"})
    unmapped_html = unmapped_only.content.decode()
    assert unmapped_only.status_code == 200
    assert "Unmapped Mutton" in unmapped_html
