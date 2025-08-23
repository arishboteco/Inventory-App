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
    form = ItemForm()
    base_field = form.fields["base_unit"]
    purchase_field = form.fields["purchase_unit"]
    assert base_field.label == "Base unit"
    assert base_field.max_length == 50
    assert isinstance(base_field.widget, forms.Select)
    assert purchase_field.label == "Purchase unit"
    assert purchase_field.max_length == 50
    assert isinstance(purchase_field.widget, forms.Select)


@pytest.mark.django_db
def test_purchase_unit_includes_base(monkeypatch):
    monkeypatch.setattr(forms_module, "get_units", lambda: {"kg": ["kg", "g"]})
    form = ItemForm(data={"base_unit": "kg"})
    purchase_choices = [c[0] for c in form.fields["purchase_unit"].choices]
    assert "kg" in purchase_choices


@pytest.mark.django_db
def test_item_form_units_fallback(monkeypatch, caplog):
    def fail():
        raise Exception("boom")

    monkeypatch.setattr(forms_module, "get_units", fail)
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


