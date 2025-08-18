import pytest
from inventory.models import Item
from inventory.services import item_service

@pytest.mark.django_db
def test_add_new_item_inserts_row():
    details = {
        "name": "Widget",
        "base_unit": "pcs",
        "purchase_unit": "box",
        "category": "cat",
        "sub_category": "sub",
        "permitted_departments": "dept",
        "reorder_point": 1,
        "current_stock": 0,
        "notes": "n",
        "is_active": True,
    }
    success, msg = item_service.add_new_item(details)
    assert success
    assert Item.objects.filter(name="Widget").exists()

@pytest.mark.django_db
def test_get_all_items_with_stock():
    Item.objects.create(name="Item 1", base_unit="pcs", is_active=True)
    Item.objects.create(name="Item 2", base_unit="pcs", is_active=True)
    Item.objects.create(name="Item 3", base_unit="pcs", is_active=False)

    items = item_service.get_all_items_with_stock()
    assert items.count() == 2

    all_items = item_service.get_all_items_with_stock(include_inactive=True)
    assert all_items.count() == 3

@pytest.mark.django_db
def test_get_item_details():
    item = Item.objects.create(name="Item 1", base_unit="pcs")
    details = item_service.get_item_details(item.pk)
    assert details is not None
    assert details.name == "Item 1"

@pytest.mark.django_db
def test_suggest_category_and_units():
    Item.objects.create(name="Fresh Milk", base_unit="L", purchase_unit="case", category="Dairy")
    base, purchase, category = item_service.suggest_category_and_units("Whole Milk")
    assert (base, purchase, category) == ("L", "case", "Dairy")

@pytest.mark.django_db
def test_add_items_bulk_inserts_rows():
    items = [
        {"name": "Widget", "base_unit": "pcs"},
        {"name": "Gadget", "base_unit": "pcs"},
    ]
    inserted, errors = item_service.add_items_bulk(items)
    assert inserted == 2
    assert not errors
    assert Item.objects.filter(name__in=["Widget", "Gadget"]).count() == 2

@pytest.mark.django_db
def test_add_items_bulk_validation_failure():
    items = [
        {"name": "Widget", "base_unit": "pcs"},
        {"name": "", "base_unit": "pcs"},
    ]
    inserted, errors = item_service.add_items_bulk(items)
    assert inserted == 0
    assert errors
    assert Item.objects.count() == 0

@pytest.mark.django_db
def test_remove_items_bulk_marks_inactive():
    item1 = Item.objects.create(name="Widget", is_active=True)
    item2 = Item.objects.create(name="Gadget", is_active=True)

    removed, errors = item_service.remove_items_bulk([item1.pk, item2.pk])
    assert removed == 2
    assert not errors

    item1.refresh_from_db()
    item2.refresh_from_db()

    assert not item1.is_active
    assert not item2.is_active

@pytest.mark.django_db
def test_update_item_details():
    item = Item.objects.create(name="Test Item")
    success, msg = item_service.update_item_details(item.pk, {"name": "Updated Name"})
    assert success
    item.refresh_from_db()
    assert item.name == "Updated Name"

@pytest.mark.django_db
def test_deactivate_item():
    item = Item.objects.create(name="Test Item", is_active=True)
    success, msg = item_service.deactivate_item(item.pk)
    assert success
    item.refresh_from_db()
    assert not item.is_active

@pytest.mark.django_db
def test_reactivate_item():
    item = Item.objects.create(name="Test Item", is_active=False)
    success, msg = item_service.reactivate_item(item.pk)
    assert success
    item.refresh_from_db()
    assert item.is_active
