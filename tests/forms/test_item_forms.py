"""Simplified ItemForm for testing with the units table architecture."""

from django import forms

from inventory.models import Item

INPUT_CLASS = "form-input"


class TestItemForm(forms.ModelForm):
    """Simplified item form for testing using unit_id field."""

    unit_id = forms.IntegerField(
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "placeholder": "Unit ID"})
    )

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
            "name": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Enter item name"}
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

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.unit_id = self.cleaned_data["unit_id"]
        if commit:
            instance.save()
            self.save_m2m()
        return instance
