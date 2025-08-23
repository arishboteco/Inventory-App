import pytest
from django import forms
from django.template.loader import render_to_string
from django.test import RequestFactory

from django.urls import reverse

from inventory.forms.item_forms import ItemForm
from inventory.forms import item_forms as forms_module
from inventory.services import supabase_units


@pytest.mark.django_db
def test_item_form_preserves_metadata(monkeypatch):
    monkeypatch.setattr(forms_module, "get_units", lambda: {"kg": ["g"]})
    monkeypatch.setattr(forms_module, "get_categories", lambda: {})
    form = ItemForm()
    base_field = form.fields["base_unit"]
    purchase_field = form.fields["purchase_unit"]
    assert base_field.label == "Base unit"
    assert base_field.max_length == 50
    assert isinstance(base_field.widget, forms.TextInput)
    assert base_field.widget.attrs.get("list") == "base-unit-options"
    assert purchase_field.label == "Purchase unit"
    assert purchase_field.max_length == 50
    assert isinstance(purchase_field.widget, forms.TextInput)
    assert purchase_field.widget.attrs.get("list") == "purchase-unit-options"


@pytest.mark.django_db
def test_purchase_unit_includes_base(monkeypatch):
    monkeypatch.setattr(forms_module, "get_units", lambda: {"kg": ["kg", "g"]})
    monkeypatch.setattr(forms_module, "get_categories", lambda: {})
    form = ItemForm(data={"base_unit": "kg"})
    request = RequestFactory().get("/")
    content = render_to_string(
        "inventory/item_form.html",
        {"form": form, "is_edit": False, "excluded_fields": []},
        request=request,
    )
    assert '<datalist id="purchase-unit-options">' in content
    assert '<option value="kg"></option>' in content


@pytest.mark.django_db
def test_item_form_units_fallback(monkeypatch, caplog):
    def fail():
        raise Exception("boom")

    monkeypatch.setattr(forms_module, "get_units", fail)
    monkeypatch.setattr(forms_module, "get_categories", lambda: {})
    with caplog.at_level("ERROR"):
        form = ItemForm()
    assert form.units_map == {}
    request = RequestFactory().get("/")
    content = render_to_string(
        "inventory/item_form.html",
        {"form": form, "is_edit": False, "excluded_fields": []},
        request=request,
    )
    assert "Could not load unit options" in content
    assert "Failed to load units map" in caplog.text


@pytest.mark.django_db
def test_item_form_categories_and_save(monkeypatch):
    monkeypatch.setattr(forms_module, "get_units", lambda: {"kg": ["g"]})
    monkeypatch.setattr(
        forms_module,
        "get_categories",
        lambda: {None: [{"id": 1, "name": "Food"}], "Food": [{"id": 2, "name": "Fruit"}]},
    )

    form = ItemForm()
    assert "Food" in form.category_options

    form = ItemForm(data={"category": "Food"})
    assert "Fruit" in form.sub_category_options

    data = {
        "name": "Apple",
        "base_unit": "kg",
        "purchase_unit": "g",
        "category": "Food",
        "sub_category": "Fruit",
        "is_active": True,
    }
    form = ItemForm(data=data)
    assert form.is_valid()
    item = form.save()
    assert item.category_id == 2


