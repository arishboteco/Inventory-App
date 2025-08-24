import pytest
from datetime import timedelta
from django.utils import timezone

from inventory.models import StockTransaction
from inventory.services import kpis


@pytest.mark.django_db
def test_kpi_calculations(item_factory):
    item1 = item_factory(name="A", reorder_point=20, current_stock=10)
    item2 = item_factory(name="B", reorder_point=1, current_stock=5)
    week_ago = timezone.now() - timedelta(days=2)
    StockTransaction.objects.create(item=item1, quantity_change=5, transaction_type="RECEIVING", transaction_date=week_ago)
    StockTransaction.objects.create(item=item2, quantity_change=-2, transaction_type="ISSUE", transaction_date=week_ago)

    assert kpis.stock_value() == 15
    assert kpis.receipts_last_7_days() == 5
    assert kpis.issues_last_7_days() == 2
    assert kpis.low_stock_count() == 1
    labels, values = kpis.stock_trend_last_7_days()
    assert labels and len(labels) == 7
    assert values[-1] == 3.0
