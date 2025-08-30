"""Simplified ItemForm for testing with the units table architecture."""

from django import forms

from inventory.models import Item, Unit

INPUT_CLASS = "form-input"


class TestItemForm(forms.ModelForm):
    """Simplified item form for testing that only uses unit reference."""

    unit = forms.ModelChoiceField(
        queryset=Unit.objects.all(),
        empty_label=None,
        widget=forms.Select(attrs={'class': INPUT_CLASS}),
    )

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
            'name': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Enter item name'
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        default_unit = Unit.objects.filter(is_default=True).first()
        if default_unit:
            self.fields['unit'].initial = default_unit

    def clean_unit(self):
        unit = self.cleaned_data.get('unit')
        if not unit or not Unit.objects.filter(pk=unit.pk).exists():
            raise forms.ValidationError(
                "Selected unit does not exist in units table."
            )
        return unit
