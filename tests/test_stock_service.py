import pytest
from inventory.models import Item, StockTransaction
from inventory.services import stock_service


@pytest.mark.django_db
def test_record_stock_transaction_updates_stock_and_logs():
    StockTransaction.objects.all().delete()
    Item.objects.all().delete()
    item = Item.objects.create(name="Sample", current_stock=10)
    success = stock_service.record_stock_transaction(
        item_id=item.item_id,
        quantity_change=5,
        transaction_type="RECEIVING",
        user_id="tester",
    )
    assert success
    item.refresh_from_db()
    assert item.current_stock == 15
    assert StockTransaction.objects.filter(item=item).count() == 1


@pytest.mark.django_db
def test_record_stock_transactions_bulk():
    StockTransaction.objects.all().delete()
    Item.objects.all().delete()
    item1 = Item.objects.create(name="Item1", current_stock=10)
    item2 = Item.objects.create(name="Item2", current_stock=10)
    txs = [
        {"item_id": item1.item_id, "quantity_change": 5, "transaction_type": "RECEIVING", "user_id": "u1"},
        {"item_id": item2.item_id, "quantity_change": -3, "transaction_type": "ISSUE", "user_id": "u2"},
    ]
    assert stock_service.record_stock_transactions_bulk(txs)
    item1.refresh_from_db()
    item2.refresh_from_db()
    assert item1.current_stock == 15
    assert item2.current_stock == 7
    assert StockTransaction.objects.count() == 2


@pytest.mark.django_db
def test_remove_stock_transactions_bulk():
    StockTransaction.objects.all().delete()
    Item.objects.all().delete()
    item = Item.objects.create(name="Item", current_stock=20)
    txs = [
        {"item_id": item.item_id, "quantity_change": 5, "transaction_type": "RECEIVING"},
        {"item_id": item.item_id, "quantity_change": -2, "transaction_type": "ISSUE"},
    ]
    assert stock_service.record_stock_transactions_bulk(txs)
    ids = list(StockTransaction.objects.values_list("transaction_id", flat=True))
    assert stock_service.remove_stock_transactions_bulk(ids)
    item.refresh_from_db()
    assert item.current_stock == 20
    assert StockTransaction.objects.count() == 0


@pytest.mark.django_db
def test_record_stock_transactions_bulk_rollback_on_error():
    StockTransaction.objects.all().delete()
    Item.objects.all().delete()
    item = Item.objects.create(name="Item", current_stock=10)
    txs = [
        {"item_id": item.item_id, "quantity_change": 5, "transaction_type": "RECEIVING"},
        {"item_id": 9999, "quantity_change": 3, "transaction_type": "RECEIVING"},
    ]
    assert not stock_service.record_stock_transactions_bulk(txs)
    item.refresh_from_db()
    assert item.current_stock == 10
    assert StockTransaction.objects.count() == 0


@pytest.mark.django_db
def test_remove_stock_transactions_bulk_rollback_on_error():
    StockTransaction.objects.all().delete()
    Item.objects.all().delete()
    item = Item.objects.create(name="Item", current_stock=10)
    txs = [
        {"item_id": item.item_id, "quantity_change": 5, "transaction_type": "RECEIVING"},
        {"item_id": item.item_id, "quantity_change": -2, "transaction_type": "ISSUE"},
    ]
    assert stock_service.record_stock_transactions_bulk(txs)
    ids = list(StockTransaction.objects.values_list("transaction_id", flat=True))
    valid_id = ids[0]
    item.refresh_from_db()
    current_stock = item.current_stock
    assert not stock_service.remove_stock_transactions_bulk([valid_id, 9999])
    item.refresh_from_db()
    assert item.current_stock == current_stock
    assert StockTransaction.objects.count() == 2

