from decimal import Decimal

from django import forms

from ..models import Item, Recipe, RecipeItem
from .base import StyledFormMixin

INPUT_CLASS = "w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"


class RecipeForm(StyledFormMixin, forms.ModelForm):
    # TODO: Add proper form validation and styling
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS}),
        help_text="Unique recipe name",
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": INPUT_CLASS,
                "rows": 2,
                "placeholder": "Brief recipe description...",
            }
        ),
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={"class": "h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"}
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
        widget=forms.Textarea(
            attrs={
                "class": INPUT_CLASS,
                "rows": 2,
                "placeholder": "Plating and presentation notes...",
            }
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
        min_value=0.001,
        decimal_places=3,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "step": "0.001",
                "min": "0.001",
                "placeholder": "0.000",
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


RecipeItemFormSet = forms.inlineformset_factory(
    Recipe,
    RecipeItem,
    form=RecipeItemForm,
    fields=["item", "quantity", "unit", "loss_pct"],
    extra=1,
    can_delete=True,
)