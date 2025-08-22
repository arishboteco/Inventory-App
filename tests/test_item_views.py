import pytest
from django.urls import reverse

from inventory.models import Item, StockTransaction, Category
from inventory.services import item_service

pytestmark = pytest.mark.django_db


def _create_item(category: Category | str | None = None, sub_category: Category | str | None = None, **kwargs):
    if isinstance(category, str) or category is None:
        category = Category.objects.create(name=category or "cat")
    if isinstance(sub_category, str) or sub_category is None:
        sub_category = Category.objects.create(name=sub_category or "sub", parent=category)
    defaults = {
        "name": "Widget",
        "base_unit": "pcs",
        "purchase_unit": "box",
        "category": category,
        "sub_category": sub_category,
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
    item_service.get_all_items_with_stock.clear()
    item_service.get_distinct_departments_from_items.clear()

    cat_food = Category.objects.create(id=1, name="Food")
    cat_drink = Category.objects.create(id=2, name="Drink")
    sub_fruit = Category.objects.create(id=3, name="Fruit", parent=cat_food)
    Category.objects.create(id=4, name="Soda", parent=cat_drink)
    item = _create_item(category=cat_food, sub_category=sub_fruit)

    # Prime caches
    item_service.get_all_items_with_stock()
    item_service.get_distinct_departments_from_items()
    assert item_service.get_all_items_with_stock.cache_info().currsize == 1
    assert item_service.get_distinct_departments_from_items.cache_info().currsize == 1

    url = reverse("item_edit", args=[item.pk])
    resp = client.get(url)
    assert resp.status_code == 200
    form = resp.context["form"]
    assert form.fields["category"].initial == cat_food
    assert form.fields["sub_category"].initial == sub_fruit

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
    assert item.category.name == "Drink"
    assert item.sub_category.name == "Soda"

    assert item_service.get_all_items_with_stock.cache_info().currsize == 0
    assert item_service.get_distinct_departments_from_items.cache_info().currsize == 0
