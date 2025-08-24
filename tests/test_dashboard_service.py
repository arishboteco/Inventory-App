import pytest

from inventory.services import dashboard_service


@pytest.mark.django_db
def test_get_low_stock_items(item_factory):
    item_factory(name="Low", reorder_point=10, current_stock=5)
    item_factory(name="Inactive", reorder_point=10, current_stock=5, is_active=False)
    item_factory(name="High", reorder_point=10, current_stock=15)
    items = list(dashboard_service.get_low_stock_items())
    assert [item.name for item in items] == ["Low"]
