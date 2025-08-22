import pytest
from django.urls import reverse
from django.test import RequestFactory
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage

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


def _add_messages(request):
    request.session = {}
    storage = FallbackStorage(request)
    setattr(request, "_messages", storage)


def test_item_form_adds_unit_suggestion_message(monkeypatch):
    mapping = {"kg": ["g"]}
    monkeypatch.setattr(supabase_units, "get_units", lambda force=False: mapping)
    monkeypatch.setattr("inventory.forms.get_units", lambda force=False: mapping)
    monkeypatch.setattr(unit_suggestions, "suggest_units", lambda name: ("kg", "g"))
    rf = RequestFactory()
    request = rf.post("/items/add/", {"name": "Flour"})
    _add_messages(request)
    form = ItemForm(request.POST, request=request)
    assert not form.is_valid()
    msgs = [str(m) for m in get_messages(request)]
    assert any("Base: kg" in m and "Purchase: g" in m for m in msgs)
    assert "base_unit" in form.errors
    assert "purchase_unit" in form.errors
    assert "base_unit" not in form.cleaned_data
    assert "purchase_unit" not in form.cleaned_data


def test_item_form_suggests_missing_purchase_unit(monkeypatch):
    mapping = {"kg": ["g"]}
    monkeypatch.setattr(supabase_units, "get_units", lambda force=False: mapping)
    monkeypatch.setattr("inventory.forms.get_units", lambda force=False: mapping)
    monkeypatch.setattr(unit_suggestions, "suggest_units", lambda name: ("kg", "g"))
    rf = RequestFactory()
    request = rf.post("/items/add/", {"name": "Flour", "base_unit": "kg"})
    _add_messages(request)
    form = ItemForm(request.POST, request=request)
    assert not form.is_valid()
    msgs = [str(m) for m in get_messages(request)]
    assert any("Purchase: g" in m for m in msgs)
    assert all("Base: kg" not in m for m in msgs)
    assert "purchase_unit" in form.errors
    assert "base_unit" not in form.errors
    assert form.cleaned_data.get("base_unit") == "kg"
    assert "purchase_unit" not in form.cleaned_data
