import pytest
from django.urls import reverse

from inventory.models import Item, StockTransaction

pytestmark = pytest.mark.django_db


def _create_item(**kwargs):
    defaults = {
        "name": "Widget",
        "base_unit": "pcs",
        "purchase_unit": "box",
        "category": "cat",
        "sub_category": "sub",
        "permitted_departments": "dept",
        "reorder_point": 1,
        "notes": "n",
        "is_active": True,
    }
    defaults.update(kwargs)
    return Item.objects.create(**defaults)


def test_item_detail_view(client):
    item = _create_item()
    StockTransaction.objects.create(item=item, quantity_change=5)
    url = reverse("item_detail", args=[item.pk])
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Widget" in resp.content
    assert b"Current Stock" in resp.content


def test_item_delete_view_deletes_without_transactions(client):
    item = _create_item()
    url = reverse("item_delete", args=[item.pk])
    resp = client.post(url)
    assert resp.status_code == 302
    assert Item.objects.count() == 0


def test_item_delete_view_deactivates_with_transactions(client):
    item = _create_item()
    StockTransaction.objects.create(item=item, quantity_change=2)
    url = reverse("item_delete", args=[item.pk])
    resp = client.post(url)
    assert resp.status_code == 302
    item.refresh_from_db()
    assert item.is_active is False
