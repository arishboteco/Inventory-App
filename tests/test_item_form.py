import pytest
from bs4 import BeautifulSoup
from django import forms
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse

from inventory.forms.item_forms import ItemForm
from inventory.models import Category, Department, Item, Unit
from tests.forms.test_item_forms import TestItemForm  # Use simplified test form


@pytest.mark.django_db
def test_item_form_preserves_metadata(monkeypatch):
    form = TestItemForm()
    name_field = form.fields["name"]
    unit_field = form.fields["unit_id"]
    assert name_field.label == "Name"
    assert name_field.required is True
    assert isinstance(name_field.widget, forms.TextInput)
    assert isinstance(unit_field, forms.IntegerField)


@pytest.mark.django_db
def test_item_form_validation():
    # Test valid form data with unit_id=19 (maps to "KG")
    form = TestItemForm(
        data={
            "name": "Test Item",
            "unit_id": 19,
            "reorder_point": 10,
            "current_stock": 0,
            "notes": "Test notes",
            "is_active": True,
        }
    )
    assert form.is_valid(), f"Form errors: {form.errors}"

    # Test invalid form data (missing required name)
    form = TestItemForm(
        data={
            "unit_id": 19,
            "reorder_point": 10,
        }
    )
    assert not form.is_valid()
    assert "name" in form.errors


@pytest.mark.django_db
def test_item_form_save():
    form = TestItemForm(
        data={
            "name": "Test Item",
            "unit_id": 19,
            "reorder_point": 10,
            "current_stock": 5,
            "notes": "Test notes",
            "is_active": True,
        }
    )
    assert form.is_valid(), f"Form errors: {form.errors}"
    item = form.save()
    assert item.name == "Test Item"
    assert item.unit_id == 19
    assert item.reorder_point == 10
    assert item.current_stock == 5
    assert item.notes == "Test notes"
    assert item.is_active is True


@pytest.mark.django_db
def test_item_form_uses_model_choice_fields():
    form = ItemForm()
    unit_field = form.fields["unit_id"]
    category_field = form.fields["category_id"]
    assert isinstance(unit_field, forms.ModelChoiceField)
    assert isinstance(category_field, forms.ModelChoiceField)
    assert list(unit_field.queryset) == list(
        Unit.objects.all().order_by("base_unit", "purchase_unit")
    )
    assert list(category_field.queryset) == list(
        Category.objects.all().order_by("category", "sub_category")
    )


@pytest.mark.django_db
def test_item_edit_modal_renders_all_fields():
    unit = Unit.objects.create(purchase_unit="kg", base_unit="kg", conversion_factor=1)
    category = Category.objects.create(category="Food", sub_category="Veg")
    Department.objects.create(name="Kitchen")
    item = Item.objects.create(name="T", unit=unit, category=category)
    form = ItemForm(instance=item)
    request = RequestFactory().get("/")
    content = render_to_string(
        "inventory/_item_form_partial.html",
        {"form": form, "item": item},
        request=request,
    )
    for field in [
        "name",
        "unit_id",
        "category_id",
        "departments",
        "initial_purchase_price",
        "preferred_supplier",
        "minimum_order_qty",
        "lead_time_days",
        "reorder_point",
        "current_stock",
        "notes",
        "is_active",
    ]:
        assert f'name="{field}"' in content


@pytest.mark.django_db
def test_item_edit_partial_departments_multiselect_container():
    unit = Unit.objects.create(purchase_unit="kg", base_unit="kg", conversion_factor=1)
    category = Category.objects.create(category="Food", sub_category="Veg")
    Department.objects.create(name="Kitchen")
    item = Item.objects.create(name="T", unit=unit, category=category)
    form = ItemForm(instance=item)
    request = RequestFactory().get("/")
    content = render_to_string(
        "inventory/_item_form_partial.html", {"form": form, "item": item}, request=request
    )
    soup = BeautifulSoup(content, "html.parser")
    container = soup.find("div", {"data-multiselect": "chips"})
    assert container is not None
    classes = container.get("class", [])
    assert "grid" in classes
    checkboxes = container.find_all("input", {"type": "checkbox"})
    assert len(checkboxes) >= 1


@pytest.mark.django_db
def test_item_edit_view_returns_json(client):
    unit = Unit.objects.create(purchase_unit="kg", base_unit="kg", conversion_factor=1)
    category = Category.objects.create(category="Food", sub_category="Veg")
    item = Item.objects.create(name="T", unit=unit, category=category)
    url = reverse("item_edit", args=[item.pk])
    resp = client.post(
        url,
        {
            "name": "T2",
            "unit_id": unit.pk,
            "category_id": category.pk,
            "reorder_point": 1,
            "current_stock": 1,
            "is_active": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
