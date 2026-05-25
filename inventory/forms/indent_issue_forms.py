from __future__ import annotations

from decimal import Decimal

from django import forms

from ..models import IndentItem
from .base import INPUT_CLASS, StyledFormMixin

SOURCE_LOCATION_CHOICES = [
    ("", "Select source..."),
    ("Main Store", "Main Store"),
    ("Kitchen - Indiqube", "Kitchen - Indiqube"),
    ("Kitchen - Bagmane", "Kitchen - Bagmane"),
    ("Bar - Indiqube", "Bar - Indiqube"),
    ("Bar - Bagmane", "Bar - Bagmane"),
]


class IndentItemIssueForm(StyledFormMixin, forms.Form):
    indent_item_id = forms.IntegerField(widget=forms.HiddenInput())
    issue_qty = forms.DecimalField(min_value=Decimal("0.00"), required=False)
    source_location = forms.ChoiceField(
        choices=SOURCE_LOCATION_CHOICES,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["issue_qty"].widget = forms.NumberInput(
            attrs={"step": "0.01", "class": INPUT_CLASS}
        )
        self.fields["source_location"].widget = forms.Select(
            choices=SOURCE_LOCATION_CHOICES, attrs={"class": INPUT_CLASS}
        )
        self.apply_styling()

    def clean_issue_qty(self):
        qty = self.cleaned_data.get("issue_qty")
        if qty is None:
            return Decimal("0")
        return qty


class IndentIssueFormset(forms.BaseFormSet):
    def clean(self):
        super().clean()
        # No global validation beyond individual lines

    @classmethod
    def initial_for_indent(cls, indent_id: int) -> list[dict]:
        rows = (
            IndentItem.objects.select_related("item")
            .filter(indent_id=indent_id)
            .order_by("indent_item_id")
            .values(
                "indent_item_id",
                "requested_qty",
                "issued_qty",
                "item__current_stock",
            )
        )
        initial = []
        for row in rows:
            requested = row["requested_qty"] or Decimal("0")
            issued = row["issued_qty"] or Decimal("0")
            available = row["item__current_stock"] or Decimal("0")
            pending = max(Decimal("0"), requested - issued)
            initial.append(
                {
                    "indent_item_id": row["indent_item_id"],
                    "issue_qty": min(pending, available),
                }
            )
        return initial
