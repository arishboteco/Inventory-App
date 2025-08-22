import pytest
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

from inventory.models import (
    Item,
    StockTransaction,
    RecipeComponent,
    Recipe,
    IndentItem,
    PurchaseOrderItem,
)
from inventory.services import stock_service
from django.db.utils import OperationalError


@pytest.fixture(autouse=True)
def clear_tables(db):
    for model in (
        RecipeComponent,
        Recipe,
        IndentItem,
        PurchaseOrderItem,
        StockTransaction,
        Item,
    ):
        try:
            model.objects.all().delete()
        except OperationalError:
            pass


@pytest.mark.django_db
def test_record_stock_transaction_updates_stock_and_logs(item_factory):
    item = item_factory(name="Sample", current_stock=10)
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
def test_record_stock_transactions_bulk(item_factory):
    item1 = item_factory(name="Item1", current_stock=10)
    item2 = item_factory(name="Item2", current_stock=10)
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
def test_remove_stock_transactions_bulk(item_factory):
    item = item_factory(name="Item", current_stock=20)
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
def test_record_stock_transactions_bulk_rollback_on_error(item_factory):
    item = item_factory(name="Item", current_stock=10)
    txs = [
        {"item_id": item.item_id, "quantity_change": 5, "transaction_type": "RECEIVING"},
        {"item_id": 9999, "quantity_change": 3, "transaction_type": "RECEIVING"},
    ]
    assert not stock_service.record_stock_transactions_bulk(txs)
    item.refresh_from_db()
    assert item.current_stock == 10
    assert StockTransaction.objects.count() == 0


@pytest.mark.django_db
def test_remove_stock_transactions_bulk_rollback_on_error(item_factory):
    item = item_factory(name="Item", current_stock=10)
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


@pytest.mark.django_db(transaction=True)
def test_concurrent_stock_updates(item_factory):
    item = item_factory(name="Concurrent", current_stock=0)

    def worker():
        for _ in range(5):
            if stock_service.record_stock_transaction(
                item_id=item.item_id,
                quantity_change=1,
                transaction_type="TEST",
            ):
                break

    with ThreadPoolExecutor(max_workers=5) as executor:
        for _ in range(5):
            executor.submit(worker)

    item.refresh_from_db()
    assert item.current_stock == Decimal("5")
    assert StockTransaction.objects.filter(item=item).count() == 5
