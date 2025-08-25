import pytest

from inventory.services import dashboard_service


@pytest.mark.django_db
def test_get_low_stock_items(item_factory):
    item_factory(name="Low", reorder_point=10, current_stock=5)
    item_factory(name="Inactive", reorder_point=10, current_stock=5, is_active=False)
    item_factory(name="High", reorder_point=10, current_stock=15)
    items = list(dashboard_service.get_low_stock_items())
    assert len(items) == 1
    item = items[0]
    assert item.name == "Low"
    assert item.uom == "kg"
    assert item.current_stock == 5
    assert item.reorder_point == 10
