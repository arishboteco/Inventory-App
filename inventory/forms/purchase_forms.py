import re
from decimal import Decimal

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


def _resolve_supplier_from_raw(raw: str) -> Supplier:
    """Map typed datalist / POST value to a Supplier (active only)."""
    raw = str(raw or "").strip()
    if not raw:
        raise forms.ValidationError("Choose a valid supplier from the list.")

    qs = Supplier.objects.filter(is_active=True)

    m = re.match(r"^(\d+)\s*[-–]\s*(.+)$", raw)
    if m:
        found = qs.filter(pk=int(m.group(1))).first()
        if found:
            return found

    if raw.isdigit():
        found = qs.filter(pk=int(raw)).first()
        if found:
            return found

    exact = qs.filter(name__iexact=raw).first()
    if exact:
        return exact

    candidates = list(qs.filter(name__istartswith=raw)[:2])
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise forms.ValidationError(
            "Multiple suppliers match. Please choose from the list."
        )

    raise forms.ValidationError("Choose a valid supplier from the list.")


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
        # Prevent setting SENT directly in the form (use "Send to Supplier" button instead)
        try:
            status_field = self.fields.get("status")
            if status_field and getattr(status_field, "choices", None):
                current_status = str(getattr(self.instance, "status", "") or "").upper()
                filtered = [
                    (v, lbl)
                    for v, lbl in status_field.choices
                    if str(v).upper() != "SENT" or current_status == "SENT"
                ]
                status_field.choices = filtered
        except Exception:
            pass
        if supplier_suggest_url:
            supplier_label = self.fields["supplier"].label
            self.fields["supplier"] = forms.CharField(
                label=supplier_label,
                required=True,
                widget=forms.TextInput(
                    attrs={
                        "data-predictive-input": "1",
                        "autocomplete": "off",
                        "autocapitalize": "none",
                        "autocorrect": "off",
                        "spellcheck": "false",
                        "placeholder": "Type to search suppliers...",
                        "hx-get": supplier_suggest_url,
                        "hx-trigger": "keyup changed delay:300ms",
                        "hx-target": "#supplier-options",
                        "hx-swap": "innerHTML",
                        "list": "supplier-options",
                    }
                ),
            )
            if getattr(self.instance, "pk", None) and getattr(
                self.instance, "supplier_id", None
            ):
                try:
                    self.initial["supplier"] = self.instance.supplier.name
                except Supplier.DoesNotExist:
                    pass
        self.apply_styling()

    def clean_supplier(self):
        if not isinstance(self.fields["supplier"], forms.CharField):
            return self.cleaned_data.get("supplier")
        return _resolve_supplier_from_raw(self.cleaned_data.get("supplier", ""))


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
                        f"Quantity ({quantity}) for '{item.name}' is below its "
                        f"minimum order quantity ({item.minimum_order_qty})."
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


class AdhocGRNForm(StyledFormMixin, forms.ModelForm):
    """D6: GRN header form for ad-hoc receipts (no PO required)."""

    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True).order_by("name"),
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
        empty_label="— Select supplier —",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
    )
    delivery_note_number = forms.CharField(
        required=False,
        label="Delivery Note / Invoice #",
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASS, "placeholder": "e.g. INV-2024-001"}
        ),
    )

    class Meta:
        model = GoodsReceivedNote
        fields = ["supplier", "received_date", "delivery_note_number", "notes"]
        widgets = {
            "received_date": forms.DateInput(
                attrs={"type": "date", "class": INPUT_CLASS}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()


class AdhocGRNLineForm(StyledFormMixin, forms.Form):
    """D6: A single line item for an ad-hoc GRN."""

    item = forms.ModelChoiceField(
        queryset=Item.objects.filter(is_active=True).order_by("name"),
        empty_label="— Select item —",
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    quantity_received = forms.DecimalField(
        min_value=Decimal("0.01"),
        decimal_places=2,
        label="Quantity",
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "step": "0.01",
                "min": "0.01",
                "placeholder": "0.00",
            }
        ),
    )
    unit_price = forms.DecimalField(
        min_value=Decimal("0"),
        decimal_places=2,
        required=False,
        label="Unit Price",
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "step": "0.01",
                "min": "0",
                "placeholder": "0.00",
            }
        ),
    )
    item_notes = forms.CharField(
        required=False,
        label="Notes",
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Optional"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()


AdhocGRNLineFormSet = forms.formset_factory(
    AdhocGRNLineForm, extra=3, min_num=1, validate_min=True, can_delete=False
)


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
