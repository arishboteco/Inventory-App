from __future__ import annotations

from django import forms

from ..models import Item, StockTransaction
from .base import INPUT_CLASS, StyledFormMixin


class ItemNameResolutionMixin:
    def clean_item(self):
        # Normalize the raw input from the bound data or cleaned_data
        raw = (
            (self.cleaned_data.get("item") if hasattr(self, "cleaned_data") else None)
            or self.data.get(self.add_prefix("item"))
            or ""
        )
        raw = str(raw).strip()
        if not raw:
            raise forms.ValidationError("Choose a valid item from the list.")

        # Support combined patterns like "123 - Name" or "Name (ID: 123)"
        import re
        m = re.match(r"^(\d+)\s*[-–]\s*(.+)$", raw)
        if m:
            try:
                found = Item.objects.filter(pk=int(m.group(1))).first()
                if found:
                    return found
            except Exception:
                pass
        m2 = re.search(r"\(\s*id\s*[:#-]?\s*(\d+)\s*\)$", raw, re.IGNORECASE)
        if m2:
            try:
                found = Item.objects.filter(pk=int(m2.group(1))).first()
                if found:
                    return found
            except Exception:
                pass

        # 1) Allow numeric ID
        if raw.isdigit():
            found = Item.objects.filter(pk=int(raw)).first()
            if found:
                return found

        # 2) Exact (case-insensitive) name match
        exact = Item.objects.filter(name__iexact=raw).first()
        if exact:
            return exact

        # 3) Unique prefix/startswith match (case-insensitive) to tolerate partials
        #    Only accept if there is a single unambiguous match.
        qs = Item.objects.filter(name__istartswith=raw)[:2]
        matches = list(qs)
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Ambiguous name: force the user to pick one from the dropdown
            raise forms.ValidationError("Multiple items match. Please choose from the list.")

        # Nothing matched
        raise forms.ValidationError("Choose a valid item from the list.")


class StockReceivingForm(ItemNameResolutionMixin, StyledFormMixin, forms.ModelForm):
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT_CLASS}),
    )

    class Meta:
        model = StockTransaction
        fields = ["item", "quantity_change", "related_po", "notes"]
        labels = {
            "quantity_change": "Quantity",
            "related_po": "PO ID",
        }

    def __init__(self, *args, item_suggest_url: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        item_attrs = {
            "class": INPUT_CLASS,
            "data-predictive-input": "1",
            "autocomplete": "off",
            "autocapitalize": "none",
            "autocorrect": "off",
            "spellcheck": "false",
        }
        if item_suggest_url:
            item_attrs.update(
                {
                    "hx-get": item_suggest_url,
                    "hx-trigger": "keyup changed delay:500ms",
                    "hx-target": "#item-options",
                    "list": "item-options",
                }
            )
        # Accept name-first: override ModelChoiceField with CharField, resolve in clean_item()
        self.fields["item"] = forms.CharField(label="Item", required=True, widget=forms.TextInput(attrs=item_attrs))
        # Predictive PO only (user is auto-populated from request)
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
                    "autocapitalize": "none",
                    "autocorrect": "off",
                    "spellcheck": "false",
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
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT_CLASS}),
    )

    class Meta:
        model = StockTransaction
        fields = ["item", "quantity_change", "notes"]
        labels = {"quantity_change": "Quantity Change"}

    def __init__(self, *args, item_suggest_url: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        item_attrs = {
            "class": INPUT_CLASS,
            "data-predictive-input": "1",
            "autocomplete": "off",
            "autocapitalize": "none",
            "autocorrect": "off",
            "spellcheck": "false",
        }
        if item_suggest_url:
            item_attrs.update(
                {
                    "hx-get": item_suggest_url,
                    "hx-trigger": "keyup changed delay:500ms",
                    "hx-target": "#item-options",
                    "list": "item-options",
                }
            )
        self.fields["item"] = forms.CharField(label="Item", required=True, widget=forms.TextInput(attrs=item_attrs))
        self.apply_styling()

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        obj.transaction_type = "ADJUSTMENT"
        if commit:
            obj.save()
        return obj


class StockWastageForm(ItemNameResolutionMixin, StyledFormMixin, forms.ModelForm):
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT_CLASS}),
    )

    class Meta:
        model = StockTransaction
        fields = ["item", "quantity_change", "notes"]
        labels = {"quantity_change": "Quantity"}

    def __init__(self, *args, item_suggest_url: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        item_attrs = {
            "class": INPUT_CLASS,
            "data-predictive-input": "1",
            "autocomplete": "off",
            "autocapitalize": "none",
            "autocorrect": "off",
            "spellcheck": "false",
        }
        if item_suggest_url:
            item_attrs.update(
                {
                    "hx-get": item_suggest_url,
                    "hx-trigger": "keyup changed delay:500ms",
                    "hx-target": "#item-options",
                    "list": "item-options",
                }
            )
        self.fields["item"] = forms.CharField(label="Item", required=True, widget=forms.TextInput(attrs=item_attrs))
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


class StockBulkUploadForm(StyledFormMixin, forms.Form):
    file = forms.FileField()
