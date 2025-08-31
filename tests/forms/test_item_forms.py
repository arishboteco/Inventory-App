"""Simplified ItemForm for testing with the units table architecture."""

from django import forms

from inventory.models import Item

INPUT_CLASS = "form-input"


class TestItemForm(forms.ModelForm):
    """Simplified item form for testing that only uses unit reference."""

    class Meta:
        model = Item
        fields = [
            "name",
            "unit",
            "reorder_point",
            "current_stock",
            "notes",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Enter item name"}
            ),
            "unit": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Unit ID"}
            ),
            "reorder_point": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "10.00",
                }
            ),
            "current_stock": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "0.00",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": INPUT_CLASS,
                    "rows": 3,
                    "placeholder": "Additional notes about this item",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }
        error_messages = {
            "name": {"required": "Item name is required."},
        }

    pass
