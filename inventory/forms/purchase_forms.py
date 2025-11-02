from datetime import date, timedelta

from django import forms

from ..models import GoodsReceivedNote, GRNItem, Item, PurchaseOrder, PurchaseOrderItem, Supplier
from .base import INPUT_CLASS, StyledFormMixin


class PurchaseOrderForm(StyledFormMixin, forms.ModelForm):
    """Enhanced Purchase Order form with proper widgets and smart defaults."""

    # Override supplier to use proper select dropdown
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True).order_by('name'),
        empty_label="Select Supplier",
        required=True,
        help_text="Choose the supplier for this purchase order",
        widget=forms.Select(attrs={"class": INPUT_CLASS + " predictive"}),
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": INPUT_CLASS,
            "rows": 3,
            "placeholder": "Add notes about this purchase order..."
        }),
        help_text="Optional notes or special instructions",
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
        widgets = {
            "order_date": forms.DateInput(attrs={
                "type": "date",
                "class": INPUT_CLASS,
            }),
            "expected_delivery_date": forms.DateInput(attrs={
                "type": "date",
                "class": INPUT_CLASS,
            }),
        }
        help_texts = {
            "order_date": "Date when the order was placed",
            "expected_delivery_date": "Estimated delivery date from supplier",
            "status": "Current status of this purchase order",
        }

    def __init__(self, *args, supplier_suggest_url: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)

        # Set smart defaults for new forms
        if not self.instance.pk:
            today = date.today()
            self.fields["order_date"].initial = today
            # Default expected delivery to 7 days from now
            self.fields["expected_delivery_date"].initial = today + timedelta(days=7)

        # Configure date field constraints
        today = date.today()
        self.fields["order_date"].widget.attrs.update({
            "max": today.strftime("%Y-%m-%d"),  # Can't order in future
        })
        self.fields["expected_delivery_date"].widget.attrs.update({
            "min": today.strftime("%Y-%m-%d"),  # Delivery must be future
        })

        # Prevent setting ORDERED directly in the form
        # (Use "Mark as Ordered" button instead)
        try:
            status_field = self.fields.get("status")
            if status_field and getattr(status_field, "choices", None):
                filtered = [
                    (v, l)
                    for v, l in status_field.choices
                    if str(v).upper() != "ORDERED"
                ]
                status_field.choices = filtered
        except Exception:
            pass

        self.apply_styling()


class PurchaseOrderItemForm(StyledFormMixin, forms.ModelForm):
    """Enhanced purchase order item form with proper item selection and validation."""

    # Override item to use proper select dropdown
    item = forms.ModelChoiceField(
        queryset=Item.objects.filter(is_active=True).order_by('name'),
        empty_label="Select Item",
        required=True,
        help_text="Choose an item for this purchase order",
        widget=forms.Select(attrs={"class": INPUT_CLASS + " predictive"}),
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
        help_texts = {
            "quantity_ordered": "Quantity to order (in purchase units)",
            "unit_price": "Price per unit",
        }

    def __init__(self, *args, item_suggest_url: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)

        # Add helpful context to unit_price field
        if self.instance and hasattr(self.instance, "item") and self.instance.item:
            try:
                item = self.instance.item
                help_parts = []

                # Show last purchase price if available
                if item.last_purchase_price:
                    help_parts.append(f"Last price: ${item.last_purchase_price:.2f}")

                # Show item unit
                if hasattr(item, 'unit') and item.unit:
                    help_parts.append(f"Unit: {item.unit}")

                if help_parts:
                    self.fields["unit_price"].help_text = " | ".join(help_parts)

                # Auto-populate unit price from last purchase price
                if item.last_purchase_price and not self.instance.pk:
                    self.fields["unit_price"].initial = item.last_purchase_price

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
    fields=["item", "quantity_ordered", "unit_price"],
    extra=1,
    can_delete=True,
)


class GRNForm(StyledFormMixin, forms.ModelForm):
    """Goods Received Note form with proper date widget."""

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": INPUT_CLASS,
            "rows": 3,
            "placeholder": "Add notes about this delivery..."
        }),
        help_text="Optional notes about the received goods",
    )

    class Meta:
        model = GoodsReceivedNote
        fields = ["received_date", "notes"]
        widgets = {
            "received_date": forms.DateInput(attrs={
                "type": "date",
                "class": INPUT_CLASS,
            }),
        }
        help_texts = {
            "received_date": "Date when goods were received",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set default received date to today for new GRNs
        if not self.instance.pk:
            self.fields["received_date"].initial = date.today()

        # Configure date constraints
        today = date.today()
        self.fields["received_date"].widget.attrs.update({
            "max": today.strftime("%Y-%m-%d"),  # Can't receive in future
        })

        self.apply_styling()


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
