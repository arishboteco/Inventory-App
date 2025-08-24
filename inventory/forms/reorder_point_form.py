from __future__ import annotations

from django import forms

from ..models import Item
from .base import StyledFormMixin


class ReorderPointForm(StyledFormMixin, forms.Form):
    """Form for updating reorder point on multiple items."""

    items = forms.ModelMultipleChoiceField(
        queryset=Item.objects.filter(is_active=True),
        required=True,
    )
    reorder_point = forms.DecimalField(min_value=0, required=True)
