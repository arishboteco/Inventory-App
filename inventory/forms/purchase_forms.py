from django import forms

from ..models import GoodsReceivedNote, GRNItem, PurchaseOrder, PurchaseOrderItem
from .base import INPUT_CLASS, StyledFormMixin


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

    def clean_quantity_ordered(self):
        qty = self.cleaned_data.get("quantity_ordered")
        if qty is None or qty <= 0:
            raise forms.ValidationError("Quantity must be positive")
        return qty

    def clean_unit_price(self):
        price = self.cleaned_data.get("unit_price")
        if price is None or price <= 0:
            raise forms.ValidationError("Unit price must be positive")
        return price


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
