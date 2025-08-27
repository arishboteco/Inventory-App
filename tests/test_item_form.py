import pytest
from django import forms
from django.template.loader import render_to_string
from django.test import RequestFactory

from inventory.forms import item_forms as forms_module
from inventory.forms.item_forms import ItemForm


@pytest.mark.django_db
def test_item_form_preserves_metadata(monkeypatch):
    form = ItemForm()
    name_field = form.fields["name"]
    unit_field = form.fields["unit_id"]
    assert name_field.label == "Name"
    assert name_field.required == True
    assert isinstance(name_field.widget, forms.TextInput)
    assert isinstance(unit_field, forms.IntegerField)



@pytest.mark.django_db
def test_item_form_validation():
    # Test valid form data
    form = ItemForm(data={
        "name": "Test Item",
        "unit_id": 55,
        "reorder_point": 10,
        "current_stock": 0,
        "notes": "Test notes",
        "is_active": True,
    })
    assert form.is_valid()
    
    # Test invalid form data (missing required name)
    form = ItemForm(data={
        "unit_id": 55,
        "reorder_point": 10,
    })
    assert not form.is_valid()
    assert "name" in form.errors


@pytest.mark.django_db  
def test_item_form_save():
    form = ItemForm(data={
        "name": "Test Item",
        "unit_id": 55,
        "reorder_point": 10,
        "current_stock": 5,
        "notes": "Test notes",
        "is_active": True,
    })
    assert form.is_valid()
    item = form.save()
    assert item.name == "Test Item"
    assert item.unit_id == 55
    assert item.reorder_point == 10
    assert item.current_stock == 5
    assert item.notes == "Test notes"
    assert item.is_active == True


@pytest.mark.django_db
def test_item_form_render():
    form = ItemForm()
    request = RequestFactory().get("/")
    content = render_to_string(
        "inventory/item_form.html",
        {"form": form, "is_edit": False, "excluded_fields": []},
        request=request,
    )
    # Check that the form renders without errors
    assert "name" in content.lower()
    assert "unit_id" in content.lower() or "unit" in content.lower()
