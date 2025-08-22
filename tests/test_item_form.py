import pytest
from django import forms
from django.template.loader import render_to_string
from django.test import RequestFactory

from django.urls import reverse

from inventory.forms.item_forms import ItemForm
from inventory.forms import item_forms as forms_module
from inventory.services import supabase_units, supabase_categories
from inventory.models import Category


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


@pytest.mark.django_db
def test_item_form_categories_and_subcategories(monkeypatch):
    monkeypatch.setattr(supabase_units, "get_units", lambda: {"kg": ["g"]})
    categories_map = {
        None: [{"id": 1, "name": "Food"}, {"id": 2, "name": "Tools"}],
        1: [{"id": 3, "name": "Fruit"}, {"id": 4, "name": "Veg"}],
        2: [{"id": 5, "name": "Hammer"}],
    }
    monkeypatch.setattr(forms_module, "get_categories", lambda: categories_map)
    Category.objects.create(id=1, name="Food")
    Category.objects.create(id=2, name="Tools")
    Category.objects.create(id=3, name="Fruit", parent_id=1)
    Category.objects.create(id=4, name="Veg", parent_id=1)
    Category.objects.create(id=5, name="Hammer", parent_id=2)

    form = ItemForm()
    cat_choices = [
        (("" if val is None else str(val)), label)
        for val, label in form.fields["category"].choices
    ]
    assert cat_choices == [
        ("", "---------"),
        ("1", "Food"),
        ("2", "Tools"),
    ]
    sub_choices = [
        (("" if val is None else str(val)), label)
        for val, label in form.fields["sub_category"].choices
    ]
    assert sub_choices == [("", "---------")]

    data = {
        "name": "Apple",
        "base_unit": "kg",
        "purchase_unit": "g",
        "category": "1",
        "sub_category": "3",
    }
    form = ItemForm(data=data)
    sub_choices = [
        (("" if val is None else str(val)), label)
        for val, label in form.fields["sub_category"].choices
    ]
    assert sub_choices == [
        ("", "---------"),
        ("3", "Fruit"),
        ("4", "Veg"),
    ]
    assert form.is_valid()
    item = form.save()
    assert item.category.name == "Food"
    assert item.sub_category.name == "Fruit"


@pytest.mark.django_db
def test_subcategory_options_view(client, monkeypatch):
    categories_map = {
        None: [{"id": 1, "name": "Food"}],
        1: [{"id": 3, "name": "Fruit"}, {"id": 4, "name": "Veg"}],
    }
    monkeypatch.setattr(
        supabase_categories, "get_categories", lambda: categories_map
    )
    from inventory.views import items as items_views
    monkeypatch.setattr(items_views, "get_categories", lambda: categories_map)
    url = reverse("item_subcategory_options")
    resp = client.get(url, {"category": 1})
    assert resp.status_code == 200
    content = resp.content.decode()
    assert 'value="3"' in content
    assert 'value="4"' in content
