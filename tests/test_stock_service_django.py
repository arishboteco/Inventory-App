import pytest

from inventory.models import StockTransaction
from inventory.services import stock_service


@pytest.mark.django_db
def test_record_stock_transaction_updates_stock_and_logs(item_factory):
    item = item_factory(name="Sample", current_stock=10)
    ok = stock_service.record_stock_transaction(
        item_id=item.item_id,
        quantity_change=5,
        transaction_type="RECEIVING",
        user_id="tester",
    )
    assert ok
    item.refresh_from_db()
    assert item.current_stock == 15
    assert StockTransaction.objects.filter(item=item).count() == 1


@pytest.mark.django_db
def test_record_and_remove_bulk_transactions(item_factory):
    item1 = item_factory(name="Item1", current_stock=10)
    item2 = item_factory(name="Item2", current_stock=10)
    txs = [
        {"item_id": item1.item_id, "quantity_change": 5, "transaction_type": "RECEIVING"},
        {"item_id": item2.item_id, "quantity_change": -3, "transaction_type": "ISSUE"},
    ]
    assert stock_service.record_stock_transactions_bulk(txs)
    item1.refresh_from_db()
    item2.refresh_from_db()
    assert item1.current_stock == 15
    assert item2.current_stock == 7
    ids = list(StockTransaction.objects.values_list("transaction_id", flat=True))
    assert stock_service.remove_stock_transactions_bulk(ids)
    item1.refresh_from_db()
    item2.refresh_from_db()
    assert item1.current_stock == 10
    assert item2.current_stock == 10
