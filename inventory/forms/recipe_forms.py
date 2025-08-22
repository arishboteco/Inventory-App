from django import forms

from ..models import Recipe, RecipeComponent
from .base import StyledFormMixin


class RecipeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Recipe
        fields = [
            "name",
            "description",
            "type",
            "default_yield_qty",
            "default_yield_unit",
            "plating_notes",
            "tags",
            "is_active",
        ]


class RecipeComponentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = RecipeComponent
        fields = [
            "component_kind",
            "component_id",
            "quantity",
            "unit",
            "loss_pct",
        ]


RecipeComponentFormSet = forms.inlineformset_factory(
    Recipe,
    RecipeComponent,
    form=RecipeComponentForm,
    fields=["component_kind", "component_id", "quantity", "unit", "loss_pct"],
    extra=1,
    can_delete=True,
)
