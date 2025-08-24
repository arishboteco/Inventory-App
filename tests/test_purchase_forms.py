import pytest

from inventory.forms.purchase_forms import PurchaseOrderItemForm


@pytest.mark.django_db
@pytest.mark.parametrize("qty", [0, -1])
def test_purchase_order_item_form_requires_positive_quantity(item_factory, qty):
    item = item_factory(name="Sugar")
    form = PurchaseOrderItemForm(
        data={"item": item.pk, "quantity_ordered": qty, "unit_price": 10}
    )
    assert not form.is_valid()
    assert form.errors["quantity_ordered"] == ["Quantity must be positive"]


@pytest.mark.django_db
@pytest.mark.parametrize("price", [0, -1])
def test_purchase_order_item_form_requires_positive_unit_price(item_factory, price):
    item = item_factory(name="Sugar")
    form = PurchaseOrderItemForm(
        data={"item": item.pk, "quantity_ordered": 5, "unit_price": price}
    )
    assert not form.is_valid()
    assert form.errors["unit_price"] == ["Unit price must be positive"]
