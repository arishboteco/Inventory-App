import pytest

from inventory.services.stock_utils import get_low_stock_items
from inventory.services import stock_service


@pytest.mark.django_db
def test_get_low_stock_items(item_factory):
    get_low_stock_items.clear()
    # Use unit_id=19 which maps to "KG" instead of unit_id=1 which maps to "2 KG"
    item_factory(name="Low", reorder_point=10, current_stock=5, unit_id=19)
    item_factory(name="Inactive", reorder_point=10, current_stock=5, is_active=False, unit_id=19)
    item_factory(name="High", reorder_point=10, current_stock=15, unit_id=19)
    items = get_low_stock_items()
    assert len(items) == 1
    item = items[0]
    assert item.name == "Low"
    assert item.uom == "KG"  # unit_id=19 maps to purchase_unit="KG"
    assert item.current_stock == 5
    assert item.reorder_point == 10


@pytest.mark.django_db
def test_get_low_stock_items_cache_invalidation(
    item_factory, django_assert_num_queries
):
    get_low_stock_items.clear()
    item = item_factory(name="Low", reorder_point=10, current_stock=5, unit_id=19)

    # Prime cache
    get_low_stock_items()
    with django_assert_num_queries(0):
        get_low_stock_items()

    # Increase stock to invalidate cache
    stock_service.record_stock_transaction(
        item_id=item.item_id, quantity_change=10, transaction_type="RECEIVING"
    )

    with django_assert_num_queries(1):
        items = get_low_stock_items()
    assert items == []
