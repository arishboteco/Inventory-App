from __future__ import annotations

from decimal import Decimal

from django import forms

from ..models import IndentItem
from .base import INPUT_CLASS, StyledFormMixin


class IndentItemIssueForm(StyledFormMixin, forms.Form):
    indent_item_id = forms.IntegerField(widget=forms.HiddenInput())
    issue_qty = forms.DecimalField(min_value=Decimal("0.00"), required=False)
    source_location = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["issue_qty"].widget = forms.NumberInput(
            attrs={"step": "0.01", "class": INPUT_CLASS}
        )
        self.fields["source_location"].widget = forms.TextInput(
            attrs={"placeholder": "Store/Freezer/Bin...", "class": INPUT_CLASS}
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
            .values("indent_item_id")
        )
        return [{"indent_item_id": r["indent_item_id"]} for r in rows]
