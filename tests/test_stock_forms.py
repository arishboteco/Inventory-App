import pytest
from django import forms as django_forms
from django.urls import reverse

from inventory.forms.stock_forms import (
    StockAdjustmentForm,
    StockReceivingForm,
    StockWastageForm,
)
from inventory.models import Item


@pytest.mark.django_db
def test_stock_forms_use_item_autocomplete():
    url = reverse("item_search")
    forms = [
        StockReceivingForm(item_suggest_url=url),
        StockAdjustmentForm(item_suggest_url=url),
        StockWastageForm(item_suggest_url=url),
    ]
    for form in forms:
        widget = form.fields["item"].widget
        assert isinstance(widget, django_forms.TextInput)
        attrs = widget.attrs
        assert attrs.get("list") == "item-options"
        assert attrs.get("hx-get") == url
        assert attrs.get("hx-target") == "#item-options"
        assert attrs.get("hx-trigger") == "keyup changed delay:500ms"


@pytest.mark.django_db
def test_stock_movements_page_has_datalist(client):
    url = reverse("item_search")
    resp = client.get(reverse("stock_movements"))
    content = resp.content.decode()
    assert '<datalist id="item-options">' in content
    assert f'hx-get="{url}"' in content
    assert 'hx-target="#item-options"' in content
    assert 'hx-trigger="keyup changed delay:500ms"' in content
    assert 'list="item-options"' in content


@pytest.mark.django_db
@pytest.mark.parametrize("qty", [0, -1])
def test_stock_receiving_form_requires_positive_quantity(qty):
    item = Item.objects.create(name="Test", base_unit="kg", purchase_unit="kg")
    form = StockReceivingForm(data={"item": item.pk, "quantity_change": qty})
    assert not form.is_valid()
    assert form.errors["quantity_change"] == ["Quantity must be positive"]
