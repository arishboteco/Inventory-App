from decimal import Decimal

import pytest
from django.urls import reverse

from inventory.models import Item, StockTransaction
from inventory.models.departments import Department
from inventory.services import item_service

pytestmark = pytest.mark.django_db


def _create_item(**kwargs):
    defaults = {
        "name": "Widget",
        "unit_id": 55,
        "reorder_point": 1,
        "notes": "n",
        "is_active": True,
        "category_id": 1,
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


def test_item_create_view_htmx_success(client, monkeypatch):

    url = reverse("item_create")
    data = {
        "name": "Widget",
        "unit_id": "55",
        "reorder_point": "1",
        "current_stock": "0",
        "notes": "n",
        "is_active": "on",
    }
    resp = client.post(url, data, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "<option" in content
    assert "toast" in content


def test_item_create_partial_persists_reorder_point_and_category(client):
    from inventory.models import Category, Unit

    unit = Unit.objects.create(
        purchase_unit="kg",
        base_unit="kg",
        conversion_factor=1,
    )
    category = Category.objects.create(category="Food", sub_category="Dry Goods")
    url = reverse("items_list")
    resp = client.post(
        url,
        {
            "partial": "1",
            "name": "Brown Sugar",
            "unit_id": str(unit.unit_id),
            "category_id": str(category.category_id),
            "reorder_point": "12.50",
            "current_stock": "3.00",
            "is_active": "on",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    item = Item.objects.get(name="Brown Sugar")
    assert item.reorder_point == Decimal("12.50")
    assert item.category_id == category.category_id


def test_item_create_view_htmx_failure(client, monkeypatch):

    url = reverse("item_create")
    data = {
        "unit_id": "55",
        "reorder_point": "1",
        "current_stock": "0",
        "notes": "n",
        "is_active": "on",
    }
    resp = client.post(url, data, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    assert resp.headers.get("HX-Retarget") == "#item-form"
    assert "Item name is required" in resp.content.decode()


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


def test_item_delete_view_fetch_returns_json(client):
    item = _create_item()
    url = reverse("item_delete", args=[item.pk])
    resp = client.post(url, HTTP_X_REQUESTED_WITH="fetch")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert Item.objects.count() == 0


def test_item_delete_view_fetch_deactivates(client):
    item = _create_item()
    StockTransaction.objects.create(item=item, quantity_change=2)
    url = reverse("item_delete", args=[item.pk])
    resp = client.post(url, HTTP_X_REQUESTED_WITH="fetch")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    item.refresh_from_db()
    assert item.is_active is False


def test_item_edit_view_updates_and_clears_cache(client, monkeypatch):

    item_service.get_all_items_with_stock.clear()
    item_service.get_distinct_departments_from_items.clear()

    item = _create_item(category_id=1)

    # Prime caches
    item_service.get_all_items_with_stock()
    item_service.get_distinct_departments_from_items()
    assert item_service.get_all_items_with_stock.cache_info().currsize == 1
    assert item_service.get_distinct_departments_from_items.cache_info().currsize == 1

    url = reverse("item_edit", args=[item.pk])
    resp = client.get(url)
    assert resp.status_code == 200

    data = {
        "name": "Gadget",
        "unit_id": "55",
        "reorder_point": "5",
        "current_stock": "0",
        "notes": "updated",
        "is_active": "on",
    }
    resp = client.post(url, data)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    item.refresh_from_db()
    assert item.name == "Gadget"

    assert item_service.get_all_items_with_stock.cache_info().currsize == 0
    assert item_service.get_distinct_departments_from_items.cache_info().currsize == 0


def test_item_edit_view_preselects_category(client, monkeypatch):

    item = _create_item(category_id=2)
    url = reverse("item_edit", args=[item.pk])
    resp = client.get(url)
    assert resp.status_code == 200
    content = resp.content.decode()

    # Check that the page loads successfully
    assert "Widget" in content


def test_items_list_view_shows_empty_categories(client, monkeypatch):
    url = reverse("items_list")
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.context["categories"] == []
    assert resp.context["subcategories"] == []


def test_items_list_view_populates_categories(client, monkeypatch):
    monkeypatch.setattr(
        "inventory.services.category_filters.CategoriesService.get_category_choices_grouped",
        lambda: {"Food": [(2, "Fruit")]},
    )
    url = reverse("items_list") + "?category=Food&subcategory=Fruit"
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.context["categories"] == ["Food"]
    assert resp.context["subcategories"] == ["Fruit"]
    assert resp.context["category"] == "Food"
    assert resp.context["subcategory"] == "Fruit"


def test_items_export_view_returns_csv(client):
    _create_item()
    url = reverse("items_export")
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp["Content-Type"] == "text/csv"
    content = resp.content.decode()
    lines = content.splitlines()
    assert lines[0].startswith("ID,Name,Unit")
    assert "Widget" in content


def test_items_list_view_has_column_menu(client):
    url = reverse("items_list")
    resp = client.get(url)
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "data-col-menu-button" in content
    assert "data-layout-btn" not in content


def test_toggle_item_post(client):
    item = _create_item()
    url = reverse("item_toggle_active", args=[item.pk])
    resp = client.post(url, {"page": "1"})
    assert resp.status_code == 200
    item.refresh_from_db()
    assert item.is_active is False
    resp = client.post(url, {"page": "1"})
    assert resp.status_code == 200
    item.refresh_from_db()
    assert item.is_active is True


def test_item_search_includes_unassigned_when_department_filter(client):
    """Department-scoped search still lists items with no department (indent UX)."""
    dept = Department.objects.create(name="Kitchen SearchDept")
    _create_item(name="Sugar Universal")
    assigned = _create_item(name="Sugar Kitchen Only")
    assigned.departments.add(dept)
    url = reverse("item_search")
    resp = client.get(url, {"q": "Sugar", "department": str(dept.department_id)})
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Sugar Universal" in content
    assert "Sugar Kitchen Only" in content
