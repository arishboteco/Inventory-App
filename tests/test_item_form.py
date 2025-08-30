import pytest
from django import forms
from django.template.loader import render_to_string
from django.test import RequestFactory

from inventory.models import Unit
from tests.forms.test_item_forms import TestItemForm  # Use simplified test form


@pytest.fixture
def units(db):
    Unit.objects.filter(is_default=True).update(is_default=False)
    default = Unit.objects.create(
        base_unit="kg", purchase_unit="KG", conversion_factor=1.0, is_default=True
    )
    other = Unit.objects.create(
        base_unit="g", purchase_unit="G", conversion_factor=1.0
    )
    return default, other


@pytest.mark.django_db
def test_item_form_preserves_metadata(units):
    form = TestItemForm()
    name_field = form.fields["name"]
    unit_field = form.fields["unit"]
    assert name_field.label == "Name"
    assert name_field.required is True
    assert isinstance(name_field.widget, forms.TextInput)
    assert isinstance(unit_field, forms.ModelChoiceField)


@pytest.mark.django_db
def test_item_form_validation(units):
    default_unit, _ = units
    form = TestItemForm(
        data={
            "name": "Test Item",
            "unit": default_unit.pk,
            "reorder_point": 10,
            "current_stock": 0,
            "notes": "Test notes",
            "is_active": True,
        }
    )
    assert form.is_valid(), f"Form errors: {form.errors}"

    # Test invalid form data (missing required name)
    form = TestItemForm(data={"unit": default_unit.pk, "reorder_point": 10})
    assert not form.is_valid()
    assert "name" in form.errors


@pytest.mark.django_db
def test_item_form_save(units):
    default_unit, _ = units
    form = TestItemForm(
        data={
            "name": "Test Item",
            "unit": default_unit.pk,
            "reorder_point": 10,
            "current_stock": 5,
            "notes": "Test notes",
            "is_active": True,
        }
    )
    assert form.is_valid(), f"Form errors: {form.errors}"
    item = form.save()
    assert item.name == "Test Item"
    assert item.unit == default_unit
    assert item.reorder_point == 10
    assert item.current_stock == 5
    assert item.notes == "Test notes"
    assert item.is_active is True


@pytest.mark.django_db
def test_item_form_render(units):
    form = TestItemForm()
    request = RequestFactory().get("/")
    content = render_to_string(
        "inventory/item_form.html",
        {"form": form, "is_edit": False, "excluded_fields": []},
        request=request,
    )
    # Check that the form renders without errors
    assert "name" in content.lower()
    assert "unit" in content.lower()


@pytest.mark.django_db
def test_item_form_rejects_invalid_unit(units):
    form = TestItemForm(
        data={"name": "Bad", "unit": 999, "reorder_point": 1}
    )
    assert not form.is_valid()
    assert "unit" in form.errors


@pytest.mark.django_db
def test_default_unit_preselected(units):
    default_unit, _ = units
    form = TestItemForm()
    assert form.fields["unit"].initial == default_unit
