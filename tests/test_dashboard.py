import pytest
from django.urls import reverse

from inventory.models import Item, StockTransaction


@pytest.mark.django_db
def test_dashboard_low_stock(client):
    Item.objects.create(name="Foo", reorder_point=10, current_stock=5)
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200
    assert b"Foo" in resp.content


@pytest.mark.django_db
def test_dashboard_kpis_endpoint(client):
    item1 = Item.objects.create(name="Foo", reorder_point=10, current_stock=5)
    StockTransaction.objects.create(item=item1, quantity_change=1, transaction_type="RECEIVING")

    resp = client.get(reverse("dashboard-kpis"))
    assert resp.status_code == 200
    assert b"Stock Value" in resp.content
