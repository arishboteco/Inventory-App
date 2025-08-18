import pytest
from django.db import connection

from inventory.models import Item, StockTransaction
from inventory.services import stock_service


@pytest.mark.django_db
def test_record_stock_transaction_updates_stock_and_logs():
    item = Item.objects.create(name="Sample", current_stock=10)
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


from datetime import date

@pytest.mark.django_db
def test_record_and_remove_bulk_transactions():
    item1 = Item.objects.create(name="Item1", current_stock=10)
    item2 = Item.objects.create(name="Item2", current_stock=10)
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


@pytest.mark.django_db
def test_get_stock_transactions():
    item1 = Item.objects.create(name="Item1")
    item2 = Item.objects.create(name="Item2")
    stock_service.record_stock_transaction(item1.pk, 10, "RECEIVING")
    stock_service.record_stock_transaction(item2.pk, 5, "ISSUE")

    qs = stock_service.get_stock_transactions(item_id=item1.pk)
    assert qs.count() == 1
    assert qs.first().item == item1

    qs_by_date = stock_service.get_stock_transactions(start_date=date.today())
    assert qs_by_date.count() == 2


@pytest.mark.django_db
def test_record_stock_transactions_bulk_with_status():
    item1 = Item.objects.create(name="Item1")
    txs = [
        {"item_id": item1.pk, "quantity_change": 10, "transaction_type": "RECEIVING"},
        {"item_id": 999, "quantity_change": 5, "transaction_type": "RECEIVING"},
    ]
    success_count, errors = stock_service.record_stock_transactions_bulk_with_status(txs)
    assert success_count == 1
    assert len(errors) == 1
