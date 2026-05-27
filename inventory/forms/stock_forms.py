from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from django import forms

from ..models import Item, StockTransaction
from .base import INPUT_CLASS, StyledFormMixin


class ItemNameResolutionMixin:
    """Resolve free-text item input (name or ID) to an Item instance.

    Used by forms that render item as a text input with datalist (e.g. IndentItemForm).
    Stock movement forms now use ModelChoiceField Select and no longer need this mixin,
    but it is kept here for backward compatibility.
    """

    def clean_item(self):
        raw = (
            (self.cleaned_data.get("item") if hasattr(self, "cleaned_data") else None)
            or self.data.get(self.add_prefix("item"))
            or ""
        )
        raw = str(raw).strip()
        if not raw:
            raise forms.ValidationError("Choose a valid item from the list.")

        m = re.match(r"^(\d+)\s*[-–]\s*(.+)$", raw)
        if m:
            found = Item.objects.filter(pk=int(m.group(1))).first()
            if found:
                return found

        m2 = re.search(r"\(\s*id\s*[:#-]?\s*(\d+)\s*\)$", raw, re.IGNORECASE)
        if m2:
            found = Item.objects.filter(pk=int(m2.group(1))).first()
            if found:
                return found

        if raw.isdigit():
            found = Item.objects.filter(pk=int(raw)).first()
            if found:
                return found

        exact = Item.objects.filter(name__iexact=raw).first()
        if exact:
            return exact

        qs = Item.objects.filter(name__istartswith=raw)[:2]
        matches = list(qs)
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            raise forms.ValidationError(
                "Multiple items match. Please choose from the list."
            )

        raise forms.ValidationError("Choose a valid item from the list.")


WASTAGE_CATEGORIES = [
    ("SPOILED", "Spoiled"),
    ("EXPIRED", "Expired"),
    ("OVER_PREPPED", "Over-prepped"),
    ("BURNT", "Burnt"),
    ("RETURNED", "Returned"),
    ("BREAKAGE", "Breakage"),
    ("STAFF_MEAL", "Staff meal"),
    ("OTHER", "Other"),
]

ADJUSTMENT_REASONS = [
    ("STOCKCOUNT", "Stock Count Correction"),
    ("DAMAGE", "Damage"),
    ("TRANSFER", "Inter-Branch Transfer"),
    ("SYSTEM", "System Error Correction"),
    ("OTHER", "Other"),
]

SELECT_CLASS = INPUT_CLASS + " cursor-pointer"


def _item_autocomplete_field(
    item_suggest_url: str,
    *,
    label: str = "Item",
    required_message: str = "Choose a valid item from the list.",
):
    return forms.CharField(
        label=label,
        required=True,
        error_messages={"required": required_message},
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "hx-get": item_suggest_url,
                "hx-trigger": "keyup changed delay:500ms",
                "hx-target": "#item-options",
                "list": "item-options",
                "autocomplete": "off",
                "placeholder": "Type to search items...",
            }
        ),
    )


class StockReceivingForm(ItemNameResolutionMixin, StyledFormMixin, forms.ModelForm):
    use_required_attribute = False

    item = forms.ModelChoiceField(
        queryset=Item.objects.filter(is_active=True).order_by("name"),
        empty_label="— Select item —",
        error_messages={
            "required": "Choose an item to receive.",
            "invalid_choice": "Choose a valid item from the list.",
        },
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    transaction_date = forms.DateField(
        initial=date.today,
        required=False,
        label="Date",
        widget=forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
        help_text="Leave blank to use today's date",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
    )

    class Meta:
        model = StockTransaction
        fields = ["item", "quantity_change", "related_po", "transaction_date", "notes"]
        labels = {
            "quantity_change": "Quantity",
            "related_po": "PO ID (optional)",
        }

    def __init__(self, *args, item_suggest_url=None, **kwargs):
        super().__init__(*args, **kwargs)
        if item_suggest_url:
            self.fields["item"] = _item_autocomplete_field(
                item_suggest_url,
                required_message="Choose an item to receive.",
            )
        self.fields["quantity_change"].required = True
        self.fields["quantity_change"].error_messages.update(
            {
                "required": "Enter the quantity received.",
                "invalid": "Enter a valid quantity received.",
            }
        )
        self.fields["quantity_change"].widget = forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "step": "0.01",
                "min": "0.01",
                "placeholder": "e.g. 10.5",
            }
        )
        if "related_po" in self.fields:
            self.fields["related_po"].required = False
            self.fields["related_po"].label = "PO ID (optional)"
            self.fields["related_po"].widget = forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "hx-get": "/stock/pos/search/",
                    "hx-trigger": "keyup changed delay:500ms",
                    "hx-target": "#po-options",
                    "list": "po-options",
                    "autocomplete": "off",
                }
            )
        self.apply_styling()

    def clean_quantity_change(self):
        qty = self.cleaned_data.get("quantity_change")
        if qty is None or qty <= 0:
            raise forms.ValidationError("Quantity must be positive")
        return qty

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        obj.transaction_type = "RECEIVING"
        if commit:
            obj.save()
        return obj


class StockAdjustmentForm(ItemNameResolutionMixin, StyledFormMixin, forms.ModelForm):
    use_required_attribute = False

    item = forms.ModelChoiceField(
        queryset=Item.objects.filter(is_active=True).order_by("name"),
        empty_label="— Select item —",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    reason_category = forms.ChoiceField(
        choices=[("", "— Select reason —")] + ADJUSTMENT_REASONS,
        required=True,
        label="Reason",
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    transaction_date = forms.DateField(
        initial=date.today,
        required=False,
        label="Date",
        widget=forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
        help_text="Leave blank to use today's date",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
    )

    class Meta:
        model = StockTransaction
        fields = [
            "item",
            "quantity_change",
            "reason_category",
            "transaction_date",
            "notes",
        ]
        labels = {"quantity_change": "Quantity Change (+/−)"}

    def __init__(self, *args, item_suggest_url=None, **kwargs):
        super().__init__(*args, **kwargs)
        if item_suggest_url:
            self.fields["item"] = _item_autocomplete_field(
                item_suggest_url,
                required_message="Choose an item to adjust.",
            )
        else:
            self.fields["item"].error_messages.update(
                {
                    "required": "Choose an item to adjust.",
                    "invalid_choice": "Choose a valid item from the list.",
                }
            )
        self.fields["reason_category"].error_messages.update(
            {"required": "Choose why this adjustment is needed."}
        )
        self.fields["quantity_change"].label = "Quantity Change (+/-)"
        self.fields["quantity_change"].required = True
        self.fields["quantity_change"].error_messages.update(
            {
                "required": "Enter the stock change quantity.",
                "invalid": "Enter a valid stock change quantity.",
            }
        )
        self.fields["quantity_change"].widget = forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "step": "0.01",
                "placeholder": "e.g. +10 or -5",
            }
        )
        self.apply_styling()

    def clean_quantity_change(self):
        qty = self.cleaned_data.get("quantity_change")
        if qty is None or qty == 0:
            raise forms.ValidationError("Quantity change must be non-zero.")
        return qty

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        obj.transaction_type = "ADJUSTMENT"
        if commit:
            obj.save()
        return obj


class StockWastageForm(ItemNameResolutionMixin, StyledFormMixin, forms.ModelForm):
    use_required_attribute = False

    item = forms.ModelChoiceField(
        queryset=Item.objects.filter(is_active=True).order_by("name"),
        empty_label="— Select item —",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    reason_category = forms.ChoiceField(
        choices=[("", "— Select category —")] + WASTAGE_CATEGORIES,
        required=True,
        label="Wastage Category",
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    transaction_date = forms.DateField(
        initial=date.today,
        required=False,
        label="Date",
        widget=forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
        help_text="Leave blank to use today's date",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
    )
    wastage_photo = forms.FileField(
        required=False,
        label="Photo (optional)",
        widget=forms.ClearableFileInput(
            attrs={
                "class": (
                    "block w-full text-sm text-form-text border border-form-border "
                    "rounded-md cursor-pointer bg-form-bg focus:outline-none "
                    "focus:ring-2 focus:ring-primary focus:border-primary"
                ),
                "accept": ".jpg,.jpeg,.png,.webp",
            }
        ),
        help_text="Upload a photo as evidence of wastage.",
    )

    class Meta:
        model = StockTransaction
        fields = [
            "item",
            "quantity_change",
            "reason_category",
            "transaction_date",
            "notes",
            "wastage_photo",
        ]
        labels = {"quantity_change": "Quantity"}

    def __init__(self, *args, item_suggest_url=None, **kwargs):
        super().__init__(*args, **kwargs)
        if item_suggest_url:
            self.fields["item"] = _item_autocomplete_field(
                item_suggest_url,
                required_message="Choose an item to record as wastage.",
            )
        else:
            self.fields["item"].error_messages.update(
                {
                    "required": "Choose an item to record as wastage.",
                    "invalid_choice": "Choose a valid item from the list.",
                }
            )
        self.fields["reason_category"].error_messages.update(
            {"required": "Choose a wastage category."}
        )
        self.fields["quantity_change"].required = True
        self.fields["quantity_change"].error_messages.update(
            {
                "required": "Enter the quantity wasted.",
                "invalid": "Enter a valid quantity wasted.",
            }
        )
        self.fields["quantity_change"].widget = forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "step": "0.01",
                "min": "0.01",
                "placeholder": "e.g. 5",
            }
        )
        self.apply_styling()

    def clean_quantity_change(self):
        qty = self.cleaned_data.get("quantity_change")
        if qty is None or qty <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        return qty

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        obj.transaction_type = "WASTAGE"
        obj.quantity_change = -abs(obj.quantity_change or 0)
        if commit:
            obj.save()
        return obj


class StockBulkUploadForm(StyledFormMixin, forms.Form):
    file = forms.FileField()


class StockTransferForm(StyledFormMixin, forms.Form):
    """D3: Transfer stock between departments."""

    from ..models import Department

    use_required_attribute = False

    item = forms.ModelChoiceField(
        queryset=Item.objects.filter(is_active=True).order_by("name"),
        empty_label="— Select item —",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    quantity = forms.DecimalField(
        min_value=Decimal("0.01"),
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "step": "0.01",
                "min": "0.01",
                "placeholder": "e.g. 5",
            }
        ),
        label="Quantity",
    )
    from_department = forms.ModelChoiceField(
        queryset=None,  # set in __init__
        empty_label="— From Department —",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
        label="From Department",
    )
    to_department = forms.ModelChoiceField(
        queryset=None,  # set in __init__
        empty_label="— To Department —",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
        label="To Department",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
        label="Notes",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ..models import Department as Dept

        qs = Dept.objects.all().order_by("name")
        self.fields["item"].error_messages.update(
            {
                "required": "Choose an item to transfer.",
                "invalid_choice": "Choose a valid item from the list.",
            }
        )
        self.fields["quantity"].error_messages.update(
            {
                "required": "Enter the transfer quantity.",
                "invalid": "Enter a valid transfer quantity.",
                "min_value": "Transfer quantity must be greater than zero.",
            }
        )
        self.fields["from_department"].queryset = qs
        self.fields["from_department"].error_messages.update(
            {
                "required": "Choose the department stock is moving from.",
                "invalid_choice": "Choose a valid source department.",
            }
        )
        self.fields["to_department"].queryset = qs
        self.fields["to_department"].error_messages.update(
            {
                "required": "Choose the department stock is moving to.",
                "invalid_choice": "Choose a valid destination department.",
            }
        )
        self.apply_styling()

    def clean(self):
        cleaned = super().clean()
        from_dept = cleaned.get("from_department")
        to_dept = cleaned.get("to_department")
        if from_dept and to_dept and from_dept == to_dept:
            self.add_error("to_department", "Cannot transfer to the same department.")
        return cleaned
