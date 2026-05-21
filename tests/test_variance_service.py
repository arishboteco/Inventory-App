from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from inventory.models import Recipe, RecipeItem, SaleTransaction, StockTransaction
from inventory.services.variance_service import build_variance_report

pytestmark = pytest.mark.django_db


def test_build_variance_report_computes_item_leakage(item_factory):
    item = item_factory(
        name="Phase6 Chicken",
        unit_id=19,
        current_stock=Decimal("11.00"),
        last_purchase_price=Decimal("200.00"),
    )
    recipe = Recipe.objects.create(
        name="Chicken Bowl Phase6",
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
        quantity=Decimal("10.00"),
        source=SaleTransaction.Source.MANUAL,
        sale_date=timezone.now(),
    )
    StockTransaction.objects.create(
        item=item,
        quantity_change=Decimal("3.00"),
        transaction_type="RECEIVING",
        transaction_date=timezone.now(),
    )
    StockTransaction.objects.create(
        item=item,
        quantity_change=Decimal("-2.00"),
        transaction_type="ISSUE",
        transaction_date=timezone.now(),
    )
    StockTransaction.objects.create(
        item=item,
        quantity_change=Decimal("-0.50"),
        transaction_type="WASTAGE",
        reason_category="SPOILED",
        transaction_date=timezone.now(),
    )

    today = timezone.localdate()
    report = build_variance_report(today, today)
    rows = [row for row in report["rows"] if row.item.pk == item.item_id]

    assert rows
    row = rows[0]
    assert row.unit_label == "KG"
    assert row.ideal_usage == Decimal("1.00")
    assert row.actual_usage == Decimal("2.50")
    assert row.variance_qty == Decimal("1.50")
    assert row.variance_value == Decimal("300.00")
    assert row.recorded_wastage_qty == Decimal("0.50")
    assert row.recorded_wastage_value == Decimal("100.00")
    assert row.unexplained_variance_qty == Decimal("1.00")
    assert row.unexplained_variance_value == Decimal("200.00")
    assert report["summary"]["leakage_value"] == Decimal("300.00")
    assert report["summary"]["recorded_wastage_value"] == Decimal("100.00")
    assert report["summary"]["unexplained_leakage_value"] == Decimal("200.00")


def test_build_variance_report_counts_unmapped_sales_rows(item_factory):
    item = item_factory(name="Phase6 Paneer", unit_id=19)
    SaleTransaction.objects.create(
        recipe=None,
        pos_item_name="Unmapped Paneer Dish",
        quantity=Decimal("2.00"),
        net_sales=Decimal("450.00"),
        source=SaleTransaction.Source.POS_CSV,
        sale_date=timezone.now(),
    )
    StockTransaction.objects.create(
        item=item,
        quantity_change=Decimal("-1.00"),
        transaction_type="ISSUE",
        transaction_date=timezone.now(),
    )

    today = timezone.localdate()
    report = build_variance_report(today, today)
    assert report["summary"]["unmapped_sales_count"] == 1
    assert "unexplained_leakage_value" in report["summary"]
