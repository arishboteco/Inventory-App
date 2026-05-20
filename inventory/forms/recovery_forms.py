from django import forms

from ..models import Item, SavingsLedger, Supplier, VendorItemPrice
from .base import StyledFormMixin


class SavingsLedgerForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SavingsLedger
        fields = [
            "date",
            "outlet",
            "item",
            "saving_type",
            "source_document_type",
            "source_document_id",
            "baseline_price",
            "selected_price",
            "invoice_price",
            "quantity",
            "estimated_saving",
            "confirmed_saving",
            "lost_saving",
            "status",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["item"].queryset = Item.objects.filter(is_active=True).order_by(
            "name"
        )
        self.fields["item"].required = False


class VendorItemPriceForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = VendorItemPrice
        fields = [
            "vendor",
            "item",
            "unit",
            "price",
            "effective_from",
            "source",
            "is_active",
        ]
        widgets = {
            "effective_from": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vendor"].queryset = Supplier.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["item"].queryset = Item.objects.filter(is_active=True).order_by(
            "name"
        )
        self.fields["unit"].required = False
