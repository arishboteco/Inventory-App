from decimal import Decimal

from django import forms

from ..models import Item, Recipe, RecipeItem
from .base import StyledFormMixin

INPUT_CLASS = (
    "w-full px-3 py-2 text-sm border border-gray-300 rounded-lg "
    "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
)


class RecipeForm(StyledFormMixin, forms.ModelForm):
    # TODO: Add proper form validation and styling
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS}),
        help_text="Unique recipe name",
    )
    description = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                "class": (
                    "h-4 w-4 text-blue-600 focus:ring-blue-500 "
                    "border-gray-300 rounded"
                )
            }
        ),
    )
    type = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS}),
        help_text="e.g., Main Course, Appetizer, Dessert",
    )
    default_yield_qty = forms.DecimalField(
        required=False,
        initial=Decimal("1.0"),
        decimal_places=3,
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.001"}),
        help_text="Default quantity this recipe produces",
    )
    default_yield_unit = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS}),
        help_text="Unit for the yield quantity",
    )
    plating_notes = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )
    description_and_plating = forms.CharField(
        required=False,
        label="Description & Plating Notes",
        widget=forms.Textarea(
            attrs={
                "class": INPUT_CLASS + " resize-y",
                "rows": 2,
                "style": "min-height: 2.75rem;",
                "placeholder": "Capture the story and plating cues for this recipe...",
            }
        ),
        help_text=(
            "Share the overview and plating details together so the team has a "
            "single reference."
        ),
    )

    class Meta:
        model = Recipe
        fields = [
            "name",
            "description",
            "is_active",
            "type",
            "default_yield_qty",
            "default_yield_unit",
            "plating_notes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        description = self.initial.get("description") or getattr(
            self.instance, "description", ""
        )
        plating_notes = self.initial.get("plating_notes") or getattr(
            self.instance, "plating_notes", ""
        )
        if not self.is_bound:
            parts = [
                str(part).strip()
                for part in (description, plating_notes)
                if part and str(part).strip()
            ]
            combined = "\n\n".join(parts) if parts else ""
            if combined:
                self.initial.setdefault("description_and_plating", combined)
                self.fields["description_and_plating"].initial = combined

    def clean(self):
        cleaned_data = super().clean()
        combined = cleaned_data.get("description_and_plating", "")
        combined_text = str(combined).strip()
        cleaned_data["description"] = combined_text
        cleaned_data["plating_notes"] = combined_text
        return cleaned_data


class RecipeItemForm(StyledFormMixin, forms.ModelForm):
    """Form for Recipe Items - simplified from RecipeComponent."""

    item = forms.ModelChoiceField(
        queryset=Item.objects.filter(is_active=True),
        widget=forms.Select(
            attrs={
                "class": INPUT_CLASS + " predictive",
                "data-placeholder": "Select an item",
            }
        ),
        label="Item",
        empty_label="Select an item",
    )
    quantity = forms.DecimalField(
        min_value=0.01,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "step": "0.01",
                "min": "0.01",
                "placeholder": "0.00",
            }
        ),
        label="Quantity",
    )
    unit = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )
    unit_display = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "readonly": True,
                "placeholder": "Unit",
            }
        ),
        required=False,
        label="Unit",
    )
    loss_pct = forms.DecimalField(
        initial=0,
        min_value=0,
        max_value=100,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "step": "0.01",
                "min": "0",
                "max": "100",
                "placeholder": "0.00",
            }
        ),
        label="Loss %",
    )

    class Meta:
        model = RecipeItem
        fields = [
            "item",
            "quantity",
            "unit",
            "loss_pct",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        has_instance = getattr(instance, "pk", None) is not None
        unit_value = ""
        if has_instance:
            unit_value = instance.unit or ""
            if unit_value:
                self.initial.setdefault("unit", unit_value)
                self.initial.setdefault("unit_display", unit_value)
        # Keep the form fields in sync with the initial data so the template
        # renders the stored unit immediately while the JS metadata loads.
        self.fields["unit"].initial = self.initial.get("unit", unit_value)
        self.fields["unit_display"].initial = self.initial.get(
            "unit_display", unit_value
        )


RecipeItemFormSet = forms.inlineformset_factory(
    Recipe,
    RecipeItem,
    form=RecipeItemForm,
    fields=["item", "quantity", "unit", "loss_pct"],
    extra=1,
    can_delete=True,
)

# Edit views use extra=0 so no blank row is pre-appended when existing items load.
RecipeItemEditFormSet = forms.inlineformset_factory(
    Recipe,
    RecipeItem,
    form=RecipeItemForm,
    fields=["item", "quantity", "unit", "loss_pct"],
    extra=0,
    can_delete=True,
)
