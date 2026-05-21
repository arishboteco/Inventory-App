from django import forms

from ..models import POSMenuItemMapping, Recipe
from .base import StyledFormMixin


class POSSalesImportForm(StyledFormMixin, forms.Form):
    file = forms.FileField()


class POSMenuItemMappingForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = POSMenuItemMapping
        fields = ["pos_item_name", "recipe", "is_active", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["recipe"].queryset = Recipe.objects.filter(
            is_active=True,
            type=Recipe.Type.FINAL,
        ).order_by("name")
        self.fields["recipe"].required = False
