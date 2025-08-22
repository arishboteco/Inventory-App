import pytest
from django.urls import reverse

from inventory.models import Item, Supplier, StockTransaction


@pytest.mark.django_db
def test_dashboard_low_stock(client):
    Item.objects.create(name="Foo", reorder_point=10, current_stock=5)
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200
    assert b"Foo" in resp.content


@pytest.mark.django_db
def test_dashboard_totals(client):
    item1 = Item.objects.create(name="Foo", reorder_point=10, current_stock=5)
    Item.objects.create(name="Bar", reorder_point=0, current_stock=0)
    Supplier.objects.create(name="ACME")
    Supplier.objects.create(name="Globex")
    StockTransaction.objects.create(item=item1, quantity_change=1)

    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200
    assert resp.context["total_items"] == 2
    assert resp.context["total_suppliers"] == 2
    assert resp.context["recent_transactions"] == 1
