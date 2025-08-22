import pytest
from django import forms
from django.template.loader import render_to_string
from django.test import RequestFactory

from django.urls import reverse

from inventory.forms.item_forms import ItemForm
from inventory.forms import item_forms as forms_module
from inventory.services import supabase_units
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
    with caplog.at_level("WARNING"):
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
    parent = Category.objects.create(name="Food")
    sub1 = Category.objects.create(name="Fruit", parent=parent)
    sub2 = Category.objects.create(name="Veg", parent=parent)
    other_parent = Category.objects.create(name="Tools")
    Category.objects.create(name="Hammer", parent=other_parent)

    form = ItemForm()
    cat_qs = list(form.fields["category"].queryset)
    assert cat_qs == [parent, other_parent]
    assert list(form.fields["sub_category"].queryset) == []

    data = {
        "name": "Apple",
        "base_unit": "kg",
        "purchase_unit": "g",
        "category": str(parent.pk),
        "sub_category": str(sub1.pk),
    }
    form = ItemForm(data=data)
    assert list(form.fields["sub_category"].queryset) == [sub1, sub2]
    assert form.is_valid()
    item = form.save()
    assert item.category == parent.name
    assert item.sub_category == sub1.name


@pytest.mark.django_db
def test_subcategory_options_view(client):
    parent = Category.objects.create(name="Food")
    sub1 = Category.objects.create(name="Fruit", parent=parent)
    sub2 = Category.objects.create(name="Veg", parent=parent)
    url = reverse("item_subcategory_options")
    resp = client.get(url, {"category": parent.pk})
    assert resp.status_code == 200
    content = resp.content.decode()
    assert f'value="{sub1.pk}"' in content
    assert f'value="{sub2.pk}"' in content
