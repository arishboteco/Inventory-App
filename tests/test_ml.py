from datetime import timedelta

import pytest
from django.utils import timezone

from inventory.models import Item, StockTransaction
from inventory.services import ml


def create_item(name: str) -> Item:
    return Item.objects.create(name=name, base_unit="u", purchase_unit="u")


def test_forecast_returns_expected_values(db):
    item = create_item("item1")
    now = timezone.now()
    for i in range(3):
        tx = StockTransaction.objects.create(item=item, quantity_change=10)
        tx.transaction_date = now - timedelta(days=3 - i)
        tx.save(update_fields=["transaction_date"])
    forecast = ml.forecast_item_demand(item, periods=2)
    assert len(forecast) == 2
    assert forecast == pytest.approx([10, 10], rel=0.1)


def test_abc_classification(db):
    item_a = create_item("A")
    item_b = create_item("B")
    item_c = create_item("C")
    for _ in range(10):
        StockTransaction.objects.create(item=item_a, quantity_change=10)
    for _ in range(3):
        StockTransaction.objects.create(item=item_b, quantity_change=10)
    StockTransaction.objects.create(item=item_c, quantity_change=10)
    classes = ml.abc_classification()
    assert classes[item_a.pk] == "A"
    assert classes[item_b.pk] == "B"
    assert classes[item_c.pk] == "C"
