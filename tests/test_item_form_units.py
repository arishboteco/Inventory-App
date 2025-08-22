import pytest
from django.urls import reverse

from inventory.forms import ItemForm
from inventory.services import supabase_units, unit_suggestions

pytestmark = pytest.mark.django_db

def test_item_form_uses_supabase_units(monkeypatch):
    mapping = {"kg": ["g", "lb"], "ltr": ["ml"]}
    monkeypatch.setattr(supabase_units, "get_units", lambda force=False: mapping)
    monkeypatch.setattr("inventory.forms.get_units", lambda force=False: mapping)

    form = ItemForm()
    base_choices = [c[0] for c in form.fields["base_unit"].choices]
    assert "kg" in base_choices and "ltr" in base_choices

    form = ItemForm(data={"base_unit": "kg"})
    purchase_choices = [c[0] for c in form.fields["purchase_unit"].choices]
    assert "g" in purchase_choices and "lb" in purchase_choices
    assert "ml" not in purchase_choices

def test_item_suggest_view_returns_message(client, monkeypatch):
    monkeypatch.setattr(unit_suggestions, "suggest_units", lambda name: ("kg", "g"))
    url = reverse("item_suggest")
    resp = client.get(url, {"name": "milk"})
    html = resp.content.decode()
    assert "Base: kg, Purchase: g" in html
