from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model

from ..models import (
    ChefBulletin,
    Item,
    RecoveryAction,
    SavingsLedger,
    Supplier,
    VendorItemPrice,
)
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


class RecoveryActionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = RecoveryAction
        fields = [
            "title",
            "leakage_type",
            "expected_saving",
            "assigned_to",
            "due_date",
            "linked_item",
            "linked_chef_bulletin",
            "notes",
        ]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        self.fields["assigned_to"].queryset = user_model.objects.filter(
            is_active=True
        ).order_by("username")
        self.fields["linked_item"].queryset = Item.objects.filter(is_active=True).order_by(
            "name"
        )
        self.fields["linked_item"].required = False
        self.fields["linked_chef_bulletin"].queryset = ChefBulletin.objects.select_related(
            "recipe"
        ).filter(is_open=True)
        self.fields["linked_chef_bulletin"].required = False


class RecoveryActionStatusForm(StyledFormMixin, forms.Form):
    status = forms.ChoiceField(choices=RecoveryAction.Status.choices)
    verified_saving = forms.DecimalField(
        required=False,
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )
    implemented_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        verified_saving = cleaned.get("verified_saving")
        if (
            status == RecoveryAction.Status.VERIFIED
            and (verified_saving is None or verified_saving <= 0)
        ):
            self.add_error(
                "verified_saving",
                "Verified saving must be greater than zero for verified actions.",
            )
        return cleaned
