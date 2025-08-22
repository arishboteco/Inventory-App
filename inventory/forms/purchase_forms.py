from django import forms

from ..models import (
    PurchaseOrder,
    PurchaseOrderItem,
    GoodsReceivedNote,
    GRNItem,
)
from .base import StyledFormMixin, INPUT_CLASS


class PurchaseOrderForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            "supplier",
            "order_date",
            "expected_delivery_date",
            "status",
            "notes",
        ]

    def __init__(self, *args, supplier_suggest_url: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        supplier_attrs = {"class": INPUT_CLASS}
        if supplier_suggest_url:
            supplier_attrs.update(
                {
                    "hx-get": supplier_suggest_url,
                    "hx-trigger": "keyup changed delay:500ms",
                    "hx-target": "#supplier-options",
                    "list": "supplier-options",
                }
            )
        self.fields["supplier"].widget = forms.TextInput()
        self.fields["supplier"].widget.attrs.update(supplier_attrs)
        self.apply_styling()


class PurchaseOrderItemForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ["item", "quantity_ordered", "unit_price"]

    def __init__(self, *args, item_suggest_url: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        item_attrs = {"class": INPUT_CLASS}
        if item_suggest_url:
            item_attrs.update(
                {
                    "hx-get": item_suggest_url,
                    "hx-trigger": "keyup changed delay:500ms",
                    "hx-target": "#item-options",
                    "list": "item-options",
                }
            )
        self.fields["item"].widget = forms.TextInput()
        self.fields["item"].widget.attrs.update(item_attrs)
        self.apply_styling()


PurchaseOrderItemFormSet = forms.inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    fields=["item", "quantity_ordered", "unit_price"],
    extra=1,
    can_delete=True,
)


class GRNForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = GoodsReceivedNote
        fields = ["received_date", "notes"]


GRNItemFormSet = forms.inlineformset_factory(
    GoodsReceivedNote,
    GRNItem,
    fields=[
        "po_item",
        "quantity_ordered_on_po",
        "quantity_received",
        "unit_price_at_receipt",
        "item_notes",
    ],
    extra=0,
    can_delete=False,
)
