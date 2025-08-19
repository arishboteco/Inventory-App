import pytest

from inventory.models import Item
from inventory.services import dashboard_service


@pytest.mark.django_db
def test_get_low_stock_items():
    Item.objects.create(name="Low", reorder_point=10, current_stock=5)
    Item.objects.create(name="High", reorder_point=10, current_stock=15)
    items = list(dashboard_service.get_low_stock_items())
    assert [item.name for item in items] == ["Low"]
