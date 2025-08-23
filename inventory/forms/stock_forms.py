from __future__ import annotations

from django import forms

from ..models import StockTransaction
from .base import StyledFormMixin, INPUT_CLASS


class StockReceivingForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ["item", "quantity_change", "user_id", "related_po_id", "notes"]
        labels = {
            "quantity_change": "Quantity",
            "related_po_id": "PO ID",
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
        self.apply_styling()

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        obj.transaction_type = "RECEIVING"
        if commit:
            obj.save()
        return obj


class StockAdjustmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ["item", "quantity_change", "user_id", "notes"]
        labels = {"quantity_change": "Quantity Change"}

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

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        obj.transaction_type = "ADJUSTMENT"
        if commit:
            obj.save()
        return obj


class StockWastageForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ["item", "quantity_change", "user_id", "notes"]
        labels = {"quantity_change": "Quantity"}

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

    def clean_quantity_change(self):
        qty = self.cleaned_data.get("quantity_change")
        if qty is None or qty <= 0:
            raise forms.ValidationError("Quantity must be positive")
        return qty

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        obj.transaction_type = "WASTAGE"
        obj.quantity_change = -abs(obj.quantity_change or 0)
        if commit:
            obj.save()
        return obj


class StockBulkUploadForm(forms.Form):
    file = forms.FileField()
