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
    """Enhanced purchase order item form with price history and validation."""

    # Add a display field for last purchase price
    last_purchase_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': INPUT_CLASS + ' bg-gray-100',
            'readonly': True,
            'placeholder': 'N/A'
        }),
        help_text="Last purchase price for reference"
    )

    class Meta:
        model = PurchaseOrderItem
        fields = ["item", "quantity_ordered", "unit_price", "last_purchase_price"]
        widgets = {
            'quantity_ordered': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'step': '0.01',
                'min': '0.01',
                'placeholder': '1.00'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            })
        }

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

        # If we have an instance with an item, populate last purchase price
        if self.instance and hasattr(self.instance, 'item') and self.instance.item:
            try:
                last_price = self.instance.item.last_purchase_price
                if last_price:
                    self.fields["last_purchase_price"].initial = last_price
            except AttributeError:
                pass

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
        item = cleaned_data.get('item')
        quantity = cleaned_data.get('quantity_ordered')
        unit_price = cleaned_data.get('unit_price')

        # Check minimum order quantity if item has it set
        if (
            item
            and quantity
            and hasattr(item, 'minimum_order_qty')
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
            and hasattr(item, 'last_purchase_price')
            and item.last_purchase_price
        ):
            variance = (
                abs(unit_price - item.last_purchase_price) / item.last_purchase_price
            )
            if variance > 0.2:  # 20% variance threshold
                # This could be a warning rather than an error in a real implementation
                cleaned_data['_price_variance_warning'] = (
                    f"Price variance of {variance:.1%} from last purchase price"
                )

        return cleaned_data


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
