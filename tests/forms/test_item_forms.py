"""Simplified ItemForm for testing with the units table architecture."""

from django import forms

from inventory.models import Item
from inventory.services.units_service import UnitsService

INPUT_CLASS = "form-input"


class TestItemForm(forms.ModelForm):
    """Simplified item form for testing that only uses unit_id reference."""

    class Meta:
        model = Item
        fields = [
            "name",
            "unit_id",
            "reorder_point",
            "current_stock",
            "notes",
            "is_active",
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Enter item name'
            }),
            'unit_id': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Unit ID'
            }),
            'reorder_point': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'step': '0.01',
                'min': '0',
                'placeholder': '10.00'
            }),
            'current_stock': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'notes': forms.Textarea(attrs={
                'class': INPUT_CLASS,
                'rows': 3,
                'placeholder': 'Additional notes about this item'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'})
        }
        error_messages = {
            "name": {"required": "Item name is required."},
        }

    def clean_unit_id(self):
        """Validate that the unit_id exists in the units table."""
        unit_id = self.cleaned_data.get('unit_id')
        if unit_id and not UnitsService.validate_unit_id(unit_id):
            raise forms.ValidationError(
                f"Unit ID {unit_id} does not exist in units table."
            )
        return unit_id
