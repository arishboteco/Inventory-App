import json

from django import forms

from ..models import Recipe, RecipeComponent
from .base import StyledFormMixin


class RecipeForm(StyledFormMixin, forms.ModelForm):
    tags = forms.CharField(required=False, help_text="Comma-separated tags")

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tags = self.initial.get("tags")
        if isinstance(tags, list):
            self.initial["tags"] = ", ".join(tags)

    def clean_tags(self):
        data = self.cleaned_data.get("tags")
        if not data:
            return []
        try:
            parsed = json.loads(data)
            if isinstance(parsed, list):
                return parsed
            return [parsed]
        except (TypeError, ValueError):
            return [t.strip() for t in str(data).split(",") if t.strip()]


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
