from django import forms

from ..models import (
    GoodsReceivedNote,
    GRNItem,
    Item,
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
)
from .base import INPUT_CLASS, StyledFormMixin


class PurchaseOrderForm(StyledFormMixin, forms.ModelForm):
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True).order_by("name"),
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
        empty_label="Select a supplier...",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT_CLASS}),
    )

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
        # Prevent setting ORDERED directly in the form
        try:
            status_field = self.fields.get("status")
            if status_field and getattr(status_field, "choices", None):
                filtered = [
                    (v, lbl)
                    for v, lbl in status_field.choices
                    if str(v).upper() != "ORDERED"
                ]
                status_field.choices = filtered
        except Exception:
            pass
        self.apply_styling()


class PurchaseOrderItemForm(StyledFormMixin, forms.ModelForm):
    """Enhanced purchase order item form with price history and validation."""

    item = forms.ModelChoiceField(
        queryset=Item.objects.filter(is_active=True).order_by("name"),
        widget=forms.Select(attrs={"class": INPUT_CLASS + " item-select"}),
        empty_label="Select an item...",
    )

    class Meta:
        model = PurchaseOrderItem
        fields = ["item", "quantity_ordered", "unit_price"]
        widgets = {
            "quantity_ordered": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "1.00",
                }
            ),
            "unit_price": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "0.00",
                }
            ),
        }

    def __init__(self, *args, item_suggest_url: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
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

    def clean(self):
        """Validate business rules for purchase order items."""
        cleaned_data = super().clean()
        item = cleaned_data.get("item")
        quantity = cleaned_data.get("quantity_ordered")
        unit_price = cleaned_data.get("unit_price")

        # Check minimum order quantity if item has it set
        if (
            item
            and quantity
            and hasattr(item, "minimum_order_qty")
            and item.minimum_order_qty
        ):
            if quantity < item.minimum_order_qty:
                raise forms.ValidationError(
                    (
                        f"Quantity ({quantity}) is below minimum order quantity "
                        f"({item.minimum_order_qty}) for this item"
                    )
                )

        # Price variance check - warn if price is significantly
        # different from last price
        if (
            item
            and unit_price
            and hasattr(item, "last_purchase_price")
            and item.last_purchase_price
        ):
            variance = (
                abs(unit_price - item.last_purchase_price) / item.last_purchase_price
            )
            if variance > 0.2:  # 20% variance threshold
                # This could be a warning rather than an error in a real implementation
                cleaned_data["_price_variance_warning"] = (
                    f"Price variance of {variance:.1%} from last purchase price"
                )

        return cleaned_data


PurchaseOrderItemFormSet = forms.inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True,
)


class GRNForm(StyledFormMixin, forms.ModelForm):
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT_CLASS}),
    )

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
    widgets={
        "item_notes": forms.Textarea(attrs={"class": INPUT_CLASS}),
    },
    extra=0,
    can_delete=False,
)
