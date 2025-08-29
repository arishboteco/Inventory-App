import pytest
from django import forms
from django.template.loader import render_to_string
from django.test import RequestFactory

from inventory.forms.test_item_forms import TestItemForm  # Use simplified test form


@pytest.mark.django_db
def test_item_form_preserves_metadata(monkeypatch):
    form = TestItemForm()
    name_field = form.fields["name"]
    unit_field = form.fields["unit_id"]
    assert name_field.label == "Name"
    assert name_field.required == True
    assert isinstance(name_field.widget, forms.TextInput)
    assert isinstance(unit_field, forms.IntegerField)



@pytest.mark.django_db
def test_item_form_validation():
    # Test valid form data with unit_id=19 (maps to "KG")
    form = TestItemForm(data={
        "name": "Test Item",
        "unit_id": 19,  # Use unit_id=19 which exists and maps to "KG"
        "reorder_point": 10,
        "current_stock": 0,
        "notes": "Test notes",
        "is_active": True,
    })
    assert form.is_valid(), f"Form errors: {form.errors}"

    # Test invalid form data (missing required name)
    form = TestItemForm(data={
        "unit_id": 19,
        "reorder_point": 10,
    })
    assert not form.is_valid()
    assert "name" in form.errors


@pytest.mark.django_db
def test_item_form_save():
    form = TestItemForm(data={
        "name": "Test Item",
        "unit_id": 19,  # Use unit_id=19 which exists and maps to "KG"
        "reorder_point": 10,
        "current_stock": 5,
        "notes": "Test notes",
        "is_active": True,
    })
    assert form.is_valid(), f"Form errors: {form.errors}"
    item = form.save()
    assert item.name == "Test Item"
    assert item.unit_id == 19
    assert item.reorder_point == 10
    assert item.current_stock == 5
    assert item.notes == "Test notes"
    assert item.is_active == True


@pytest.mark.django_db
def test_item_form_render():
    form = TestItemForm()
    request = RequestFactory().get("/")
    content = render_to_string(
        "inventory/item_form.html",
        {"form": form, "is_edit": False, "excluded_fields": []},
        request=request,
    )
    # Check that the form renders without errors
    assert "name" in content.lower()
    assert "unit_id" in content.lower() or "unit" in content.lower()
