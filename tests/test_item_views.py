import pytest
from django.urls import reverse

from inventory.models import Item, StockTransaction
from inventory.services import item_service, supabase_categories

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


def test_item_edit_view_updates_and_clears_cache(client, monkeypatch):
    from inventory.forms import item_forms as forms_module

    monkeypatch.setattr(forms_module, "get_units", lambda: {"pcs": ["box"]})
    categories_map = {
        None: [{"id": 1, "name": "Food"}, {"id": 2, "name": "Drink"}],
        1: [{"id": 3, "name": "Fruit"}],
        2: [{"id": 4, "name": "Soda"}],
    }
    monkeypatch.setattr(forms_module, "get_categories", lambda: categories_map)
    monkeypatch.setattr(
        supabase_categories, "get_categories", lambda: categories_map
    )
    item_service.get_all_items_with_stock.clear()
    item_service.get_distinct_departments_from_items.clear()

    item = _create_item(category="Food", sub_category="Fruit")

    # Prime caches
    item_service.get_all_items_with_stock()
    item_service.get_distinct_departments_from_items()
    assert item_service.get_all_items_with_stock.cache_info().currsize == 1
    assert item_service.get_distinct_departments_from_items.cache_info().currsize == 1

    url = reverse("item_edit", args=[item.pk])
    resp = client.get(url)
    assert resp.status_code == 200
    form = resp.context["form"]
    assert form.fields["category"].initial == "1"
    assert form.fields["sub_category"].initial == "3"

    data = {
        "name": "Gadget",
        "base_unit": "pcs",
        "purchase_unit": "box",
        "category": "2",
        "sub_category": "4",
        "permitted_departments": "dept2",
        "reorder_point": "5",
        "current_stock": "0",
        "notes": "updated",
        "is_active": "on",
    }
    resp = client.post(url, data)
    assert resp.status_code == 302
    item.refresh_from_db()
    assert item.name == "Gadget"
    assert item.category == "Drink"
    assert item.sub_category == "Soda"

    assert item_service.get_all_items_with_stock.cache_info().currsize == 0
    assert item_service.get_distinct_departments_from_items.cache_info().currsize == 0
