from django import forms
from .models import Item
from legacy_streamlit.app.core.unit_inference import infer_units


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "name",
            "base_unit",
            "purchase_unit",
            "category",
            "sub_category",
            "permitted_departments",
            "reorder_point",
            "current_stock",
            "notes",
            "is_active",
        ]

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name", "")
        category = cleaned.get("category")
        base = cleaned.get("base_unit")
        purchase = cleaned.get("purchase_unit")
        if name and (not base or not purchase):
            inferred_base, inferred_purchase = infer_units(name, category)
            if not base:
                cleaned["base_unit"] = inferred_base
            if not purchase and inferred_purchase:
                cleaned["purchase_unit"] = inferred_purchase
        return cleaned


class BulkUploadForm(forms.Form):
    file = forms.FileField()
