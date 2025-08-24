import pytest
from django.urls import reverse

from inventory.services import stock_service


@pytest.mark.django_db
def test_what_if_reorder_projection(client, item_factory):
    item = item_factory(current_stock=10, reorder_point=5)
    stock_service.record_stock_transaction(
        item_id=item.item_id,
        quantity_change=5,
        transaction_type="RECEIVING",
    )
    url = reverse("what_if_reorder")
    response = client.post(url, {"items": [item.item_id], "reorder_point": 3})
    assert response.status_code == 200
    item.refresh_from_db()
    assert item.reorder_point == 3
    expected = stock_service.get_stock_history(item.item_id)
    assert response.context["projections"][0]["history"] == expected
