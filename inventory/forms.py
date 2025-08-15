from django import forms
from .models import Item, Supplier, StockTransaction
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


class BulkDeleteForm(forms.Form):
    file = forms.FileField()


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "name",
            "contact_person",
            "phone",
            "email",
            "address",
            "notes",
            "is_active",
        ]


class StockReceivingForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ["item", "quantity_change", "user_id", "related_po_id", "notes"]
        labels = {
            "quantity_change": "Quantity",
            "related_po_id": "PO ID",
        }

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        obj.transaction_type = "RECEIVING"
        if commit:
            obj.save()
        return obj


class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ["item", "quantity_change", "user_id", "notes"]
        labels = {"quantity_change": "Quantity Change"}

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        obj.transaction_type = "ADJUSTMENT"
        if commit:
            obj.save()
        return obj


class StockWastageForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ["item", "quantity_change", "user_id", "notes"]
        labels = {"quantity_change": "Quantity"}

    def clean_quantity_change(self):
        qty = self.cleaned_data.get("quantity_change")
        if qty is None or qty <= 0:
            raise forms.ValidationError("Quantity must be positive")
        return qty

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        obj.transaction_type = "WASTAGE"
        obj.quantity_change = -abs(obj.quantity_change or 0)
        if commit:
            obj.save()
        return obj


class StockBulkUploadForm(forms.Form):
    file = forms.FileField()
