import pytest
from django import forms

from inventory.forms import ItemForm
from inventory.services import supabase_units


@pytest.mark.django_db
def test_item_form_preserves_metadata(monkeypatch):
    monkeypatch.setattr(supabase_units, "get_units", lambda: {"kg": ["g"]})
    form = ItemForm()
    base_field = form.fields["base_unit"]
    purchase_field = form.fields["purchase_unit"]
    assert base_field.label == "Base unit"
    assert base_field.max_length == 50
    assert isinstance(base_field.widget, forms.Select)
    assert purchase_field.label == "Purchase unit"
    assert purchase_field.max_length == 50
    assert isinstance(purchase_field.widget, forms.Select)
