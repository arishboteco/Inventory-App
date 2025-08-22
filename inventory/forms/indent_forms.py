from __future__ import annotations

from django import forms

from ..models import Indent, IndentItem
from .base import StyledFormMixin, INPUT_CLASS


class IndentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Indent
        fields = ["requested_by", "department", "date_required", "notes"]

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        if not obj.status:
            obj.status = "SUBMITTED"
        if commit:
            obj.save()
        return obj


class IndentItemForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = IndentItem
        fields = ["item", "requested_qty", "notes"]

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


IndentItemFormSet = forms.inlineformset_factory(
    Indent,
    IndentItem,
    form=IndentItemForm,
    fields=["item", "requested_qty", "notes"],
    extra=1,
    can_delete=True,
)
