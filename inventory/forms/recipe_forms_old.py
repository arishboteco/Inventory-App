import json

from django import forms

from ..models import Item, Recipe, RecipeItem
from ..services.form_service import FormService
from .base import INPUT_CLASS, StyledFormMixin


class RecipeForm(StyledFormMixin, forms.ModelForm):
    tags = forms.CharField(required=False, help_text="Comma-separated tags")
    plating_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}),
    )
    default_yield_qty = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=3,
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.01"}),
        help_text="Quantity produced by this recipe",
    )
    default_yield_unit = forms.ChoiceField(
        required=False,
        choices=FormService.get_base_unit_choices(),
        widget=forms.Select(attrs={"class": INPUT_CLASS + " predictive", "data-placeholder": "Select base unit"}),
        help_text="Base unit for the recipe yield",
    )

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
        widgets = {
            "description": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}),
        }

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
    # Render component selector as predictive dropdown of Items; keep kind hidden as ITEM
    component_kind = forms.CharField(widget=forms.HiddenInput(), initial="ITEM")
    component_id = forms.ChoiceField(
        choices=(),
        widget=forms.Select(
            attrs={
                "class": INPUT_CLASS + " predictive",
                "data-placeholder": "Select an item",
            }
        ),
        label="Component",
    )
    quantity = forms.DecimalField(
        min_value=0.001,
        decimal_places=3,
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.001", "min": "0.001"}),
    )
    # Hidden model-backed field to submit the item's purchase unit (for backend compatibility)
    unit = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Auto-filled from the selected item",
    )
    # Visible read-only display of the item's base unit for recipes
    unit_display = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "readonly": "readonly"}),
        label="Unit",
    )
    loss_pct = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=100,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.1", "min": "0", "max": "100"}),
        label="Loss %",
    )

    class Meta:
        model = RecipeComponent
        fields = [
            "component_kind",
            "component_id",
            "quantity",
            "unit",
            "loss_pct",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate component_id choices with all active items for predictive dropdown
        items = Item.objects.filter(is_active=True).only("item_id", "name").order_by("name")
        self.fields["component_id"].choices = [("", "Select an item")] + [
            (str(i.item_id), i.name) for i in items
        ]


RecipeComponentFormSet = forms.inlineformset_factory(
    Recipe,
    RecipeComponent,
    form=RecipeComponentForm,
    fields=["component_kind", "component_id", "quantity", "unit", "loss_pct"],
    extra=1,
    can_delete=True,
)
