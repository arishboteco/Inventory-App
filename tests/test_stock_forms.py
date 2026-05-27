import pytest
from bs4 import BeautifulSoup
from django import forms as django_forms
from django.urls import reverse

from inventory.forms.stock_forms import (
    StockAdjustmentForm,
    StockReceivingForm,
    StockTransferForm,
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
    assert 'id="modal-root"' in content
    assert "min-h-full flex items-start justify-center" in content
    assert "max-h-[calc(100vh-2rem)]" in content
    assert 'name="submit_waste"' in content
    assert 'enctype="multipart/form-data"' in content


@pytest.mark.django_db
@pytest.mark.parametrize("qty", [0, -1])
def test_stock_receiving_form_requires_positive_quantity(qty):
    item = Item.objects.create(name="Test", unit_id=55)
    form = StockReceivingForm(data={"item": item.pk, "quantity_change": qty})
    assert not form.is_valid()
    assert form.errors["quantity_change"] == ["Quantity must be positive"]


@pytest.mark.django_db
def test_stock_wastage_form_includes_phase7_reasons_and_optional_photo():
    form = StockWastageForm()
    values = [value for value, _ in form.fields["reason_category"].choices]
    assert "SPOILED" in values
    assert "EXPIRED" in values
    assert "OVER_PREPPED" in values
    assert "STAFF_MEAL" in values
    assert "wastage_photo" in form.fields
    assert form.fields["wastage_photo"].required is False


@pytest.mark.django_db
def test_stock_movement_modals_mark_required_fields_and_skip_native_prompts(client):
    resp = client.get(reverse("stock_movements"))
    content = resp.content.decode()

    for label in [
        "Item",
        "Quantity",
        "Quantity Change (+/-)",
        "Reason",
        "Wastage Category",
        "From Department",
        "To Department",
    ]:
        assert f"{label}<span class=\"text-danger\"> *</span>" in content

    for field_name in [
        "receive-item",
        "receive-quantity_change",
        "adjust-item",
        "adjust-quantity_change",
        "adjust-reason_category",
        "waste-item",
        "waste-quantity_change",
        "waste-reason_category",
        "transfer-item",
        "transfer-quantity",
        "transfer-from_department",
        "transfer-to_department",
    ]:
        assert f'name="{field_name}" required' not in content


@pytest.mark.django_db
def test_stock_forms_show_contextual_required_messages():
    receive_form = StockReceivingForm(data={}, prefix="receive")
    adjust_form = StockAdjustmentForm(data={}, prefix="adjust")
    waste_form = StockWastageForm(data={}, prefix="waste")
    transfer_form = StockTransferForm(data={}, prefix="transfer")

    assert not receive_form.is_valid()
    assert receive_form.errors["item"] == ["Choose an item to receive."]
    assert receive_form.errors["quantity_change"] == ["Enter the quantity received."]

    assert not adjust_form.is_valid()
    assert adjust_form.errors["item"] == ["Choose an item to adjust."]
    assert adjust_form.errors["quantity_change"] == ["Enter the stock change quantity."]
    assert adjust_form.errors["reason_category"] == [
        "Choose why this adjustment is needed."
    ]

    assert not waste_form.is_valid()
    assert waste_form.errors["item"] == ["Choose an item to record as wastage."]
    assert waste_form.errors["quantity_change"] == ["Enter the quantity wasted."]
    assert waste_form.errors["reason_category"] == ["Choose a wastage category."]

    assert not transfer_form.is_valid()
    assert transfer_form.errors["item"] == ["Choose an item to transfer."]
    assert transfer_form.errors["quantity"] == ["Enter the transfer quantity."]
    assert transfer_form.errors["from_department"] == [
        "Choose the department stock is moving from."
    ]
    assert transfer_form.errors["to_department"] == [
        "Choose the department stock is moving to."
    ]


@pytest.mark.django_db
def test_stock_movement_modal_post_shows_contextual_errors(client):
    resp = client.post(
        reverse("stock_movements"),
        {"submit_waste": "1"},
        follow=True,
    )
    content = resp.content.decode()

    assert "Choose an item to record as wastage." in content
    assert "Enter the quantity wasted." in content
    assert "Choose a wastage category." in content


@pytest.mark.django_db
def test_stock_movements_date_filter_has_clear_dates_control(client):
    resp = client.get(
        reverse("stock_movements"),
        {
            "item_q": "rice",
            "type": "WASTAGE",
            "date_from": "2026-05-01",
            "date_to": "2026-05-27",
        },
    )

    content = resp.content.decode()
    soup = BeautifulSoup(content, "html.parser")
    clear_dates = soup.find("a", string="Clear dates")

    assert clear_dates is not None
    href = clear_dates["href"]
    assert "item_q=rice" in href
    assert "type=WASTAGE" in href
    assert "date_from" not in href
    assert "date_to" not in href
