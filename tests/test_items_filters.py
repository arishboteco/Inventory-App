import pytest
from django.test import RequestFactory

from inventory.models import Item, Supplier, Unit
from inventory.models.category import Category
from inventory.models.departments import Department
from inventory.services import category_filters
from inventory.views.items.list import _filter_and_sort_items


@pytest.mark.django_db
def test_filter_by_supplier_and_unit():
    rf = RequestFactory()
    supplier1 = Supplier.objects.create(name="Acme")
    supplier2 = Supplier.objects.create(name="Beta")
    unit_kg = Unit.objects.create(
        purchase_unit="kg", base_unit="kg", conversion_factor=1
    )
    unit_l = Unit.objects.create(purchase_unit="l", base_unit="l", conversion_factor=1)
    item1 = Item.objects.create(
        name="Sugar",
        unit=unit_kg,
        preferred_supplier=supplier1,
        reorder_point=1,
        notes="n",
        is_active=True,
    )
    item2 = Item.objects.create(
        name="Milk",
        unit=unit_l,
        preferred_supplier=supplier2,
        reorder_point=1,
        notes="n",
        is_active=True,
    )

    request = rf.get("/items/", {"base_unit": "kg"})
    qs, params = _filter_and_sort_items(request)
    assert list(qs) == [item1]
    assert params["base_unit"] == "kg"

    request = rf.get("/items/", {"supplier": str(supplier2.pk)})
    qs, params = _filter_and_sort_items(request)
    assert list(qs) == [item2]
    assert params["supplier"] == str(supplier2.pk)


@pytest.mark.django_db
def test_category_filters_include_supplier_and_units():
    rf = RequestFactory()
    Supplier.objects.create(name="Acme")
    Unit.objects.create(purchase_unit="kg", base_unit="kg", conversion_factor=1)
    request = rf.get("/items/")
    filters = category_filters.build_filters(request)
    base_filter = next(f for f in filters if f["name"] == "base_unit")
    assert any(opt["value"] == "kg" for opt in base_filter["options"])
    supplier_filter = next(f for f in filters if f["name"] == "supplier")
    assert any(opt["label"] == "Acme" for opt in supplier_filter["options"])


@pytest.mark.django_db
def test_filter_by_multiple_departments():
    rf = RequestFactory()
    unit = Unit.objects.create(purchase_unit="kg", base_unit="kg", conversion_factor=1)
    dept1 = Department.objects.create(name="Kitchen")
    dept2 = Department.objects.create(name="Bar")
    item1 = Item.objects.create(
        name="Sugar",
        unit=unit,
        reorder_point=1,
        notes="n",
        is_active=True,
    )
    item1.departments.add(dept1)
    item2 = Item.objects.create(
        name="Salt",
        unit=unit,
        reorder_point=1,
        notes="n",
        is_active=True,
    )
    item2.departments.add(dept2)
    request = rf.get(
        "/items/",
        {"department": [str(dept1.department_id), str(dept2.department_id)]},
    )
    qs, params = _filter_and_sort_items(request)
    assert set(qs) == {item1, item2}
    assert set(params["department"]) == {
        str(dept1.department_id),
        str(dept2.department_id),
    }


@pytest.mark.django_db
def test_filter_by_subcategory():
    rf = RequestFactory()
    unit = Unit.objects.create(purchase_unit="kg", base_unit="kg", conversion_factor=1)
    cat1 = Category.objects.create(category="Food", sub_category="Spices")
    cat2 = Category.objects.create(category="Food", sub_category="Dairy")
    item1 = Item.objects.create(
        name="Sugar",
        unit=unit,
        category=cat1,
        reorder_point=1,
        notes="n",
        is_active=True,
    )
    Item.objects.create(
        name="Milk",
        unit=unit,
        category=cat2,
        reorder_point=1,
        notes="n",
        is_active=True,
    )
    request = rf.get("/items/", {"subcategory": "Spices"})
    qs, params = _filter_and_sort_items(request)
    assert list(qs) == [item1]
    assert params["subcategory"] == "Spices"
