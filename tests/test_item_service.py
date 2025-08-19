import pytest

from inventory.models import Item, StockTransaction
from inventory.services import item_service

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_tables():
    StockTransaction.objects.all().delete()
    Item.objects.all().delete()
    item_service.get_all_items_with_stock.clear()
    item_service.get_distinct_departments_from_items.clear()
    item_service.suggest_category_and_units.clear()


def test_add_new_item_inserts_row():
    details = {
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
    success, _ = item_service.add_new_item(details)
    assert success
    assert Item.objects.filter(name="Widget").exists()


def test_get_all_items_with_stock_includes_unit():
    item = Item.objects.create(
        name="Widget",
        base_unit="pcs",
        purchase_unit="box",
        category="cat",
        sub_category="sub",
        permitted_departments="dept",
        reorder_point=1,
        notes="n",
        is_active=True,
    )
    StockTransaction.objects.create(item=item, quantity_change=5)
    items = item_service.get_all_items_with_stock(include_inactive=True)
    widget = next(i for i in items if i["name"] == "Widget")
    assert widget["unit"] == "pcs"
    assert widget["current_stock"] == 5


def test_get_item_details_includes_unit():
    item = Item.objects.create(
        name="Widget",
        base_unit="pcs",
        purchase_unit="box",
        category="cat",
        sub_category="sub",
        permitted_departments="dept",
        reorder_point=1,
        notes="n",
        is_active=True,
    )
    StockTransaction.objects.create(item=item, quantity_change=5)
    details = item_service.get_item_details(item.pk)
    assert details["unit"] == "pcs"
    assert details["current_stock"] == 5


def test_suggest_category_and_units():
    Item.objects.create(
        name="Fresh Milk",
        base_unit="L",
        purchase_unit="case",
        category="Dairy",
        sub_category="General",
        permitted_departments="Kitchen",
        reorder_point=0,
        notes="",
        is_active=True,
    )
    base, purchase, category = item_service.suggest_category_and_units("Whole Milk")
    assert (base, purchase, category) == ("L", "case", "Dairy")


def test_add_items_bulk_inserts_rows():
    items = [
        {
            "name": "Widget",
            "base_unit": "pcs",
            "purchase_unit": "box",
            "category": "cat",
            "sub_category": "sub",
            "permitted_departments": "dept",
            "reorder_point": 1,
            "notes": "n",
            "is_active": True,
        },
        {
            "name": "Gadget",
            "base_unit": "pcs",
            "purchase_unit": "each",
            "category": "cat",
            "sub_category": "sub",
            "permitted_departments": "dept2",
            "reorder_point": 2,
            "notes": "n",
            "is_active": True,
        },
    ]
    inserted, errors = item_service.add_items_bulk(items)
    assert inserted == 2
    assert errors == []
    assert Item.objects.filter(name__in=["Widget", "Gadget"]).count() == 2


def test_add_items_bulk_validation_failure():
    items = [
        {"name": "Widget", "base_unit": "pcs"},
        {"name": "", "base_unit": "pcs"},
    ]
    inserted, errors = item_service.add_items_bulk(items)
    assert inserted == 0
    assert errors
    assert Item.objects.count() == 0


def test_remove_items_bulk_marks_inactive():
    widget = Item.objects.create(
        name="Widget",
        base_unit="pcs",
        purchase_unit="box",
        category="cat",
        sub_category="sub",
        permitted_departments="dept",
        reorder_point=1,
        notes="n",
        is_active=True,
    )
    gadget = Item.objects.create(
        name="Gadget",
        base_unit="pcs",
        purchase_unit="each",
        category="cat",
        sub_category="sub",
        permitted_departments="dept2",
        reorder_point=2,
        notes="n",
        is_active=True,
    )
    removed, errors = item_service.remove_items_bulk([widget.pk, gadget.pk])
    assert removed == 2
    assert errors == []
    assert Item.objects.filter(is_active=False).count() == 2


def test_remove_items_bulk_requires_ids():
    removed, errors = item_service.remove_items_bulk([])
    assert removed == 0
    assert errors


@pytest.mark.django_db
def test_update_item_changes_fields():
    item = Item.objects.create(
        name="Widget",
        base_unit="pcs",
        purchase_unit="box",
        category="cat",
        sub_category="sub",
        permitted_departments="dept",
        reorder_point=1,
        notes="n",
        is_active=True,
    )
    success, _ = item_service.update_item(item.pk, {"name": "Widget2", "reorder_point": 5})
    assert success
    item.refresh_from_db()
    assert item.name == "Widget2"
    assert item.reorder_point == 5


@pytest.mark.django_db
def test_update_item_invalid_id():
    success, _ = item_service.update_item(999, {"name": "Nope"})
    assert not success


@pytest.mark.django_db
def test_deactivate_and_reactivate_item():
    item = Item.objects.create(
        name="Widget",
        base_unit="pcs",
        purchase_unit="box",
        category="cat",
        sub_category="sub",
        permitted_departments="dept",
        reorder_point=1,
        notes="n",
        is_active=True,
    )
    ok, _ = item_service.deactivate_item(item.pk)
    assert ok
    item.refresh_from_db()
    assert item.is_active is False
    ok, _ = item_service.reactivate_item(item.pk)
    assert ok
    item.refresh_from_db()
    assert item.is_active is True

