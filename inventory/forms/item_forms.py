from django import forms
from ..models import Item

INPUT_CLASS = "form-input"


class StyledFormMixin:
    """Mixin to add consistent styling to forms."""
    pass


class ItemForm(StyledFormMixin, forms.ModelForm):

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
        error_messages = {
            "name": {"required": "Item name is required."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "name" in self.fields:
            self.fields["name"].required = True
            self.fields["name"].widget.attrs.update({"class": INPUT_CLASS})
