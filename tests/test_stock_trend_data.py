from decimal import Decimal

import pytest
from django.utils import timezone

from core.views import _stock_trend_data
from inventory.models import StockTransaction


@pytest.mark.django_db
def test_stock_trend_data_metric_switch(item_factory):
    item = item_factory(name="Metric", last_purchase_price=Decimal("2.50"))
    StockTransaction.objects.create(
        item_id=item.pk,
        quantity_change=4,
        transaction_type="RECEIVING",
        transaction_date=timezone.now(),
    )
    today = timezone.now().date()
    labels_q, values_q = _stock_trend_data(item_id=item.pk, start=today, end=today)
    labels_v, values_v = _stock_trend_data(
        item_id=item.pk, start=today, end=today, metric="value"
    )
    assert values_q == [4.0]
    assert values_v == [10.0]
    assert labels_q == labels_v == [today.strftime("%Y-%m-%d")]


@pytest.mark.django_db
def test_stock_trend_data_no_data(item_factory):
    item = item_factory(name="Empty")
    today = timezone.now().date()
    labels, values = _stock_trend_data(item_id=item.pk, start=today, end=today)
    assert labels == []
    assert values == []
