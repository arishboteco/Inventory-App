from django import forms
from .models import (
    Item,
    Supplier,
    StockTransaction,
    Indent,
    IndentItem,
    PurchaseOrder,
    PurchaseOrderItem,
    GoodsReceivedNote,
    GRNItem,
    Recipe,
    RecipeComponent,
)
from .unit_inference import infer_units


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
        error_messages = {
            "name": {"required": "Item name is required."},
            "base_unit": {"required": "Base unit is required."},
            "purchase_unit": {"required": "Purchase unit is required."},
            "category": {"required": "Category is required."},
        }

    def __init__(self, *args, suggest_url: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("name", "base_unit", "purchase_unit", "category"):
            self.fields[field].required = True

        name_attrs = {"class": "form-control"}
        if suggest_url:
            name_attrs.update(
                {
                    "hx-get": suggest_url,
                    "hx-trigger": "keyup changed delay:500ms",
                    "hx-swap": "none",
                }
            )
        self.fields["name"].widget.attrs.update(name_attrs)

        self.fields["base_unit"].widget.attrs.update(
            {"id": "id_base_unit", "class": "form-control"}
        )
        self.fields["purchase_unit"].widget.attrs.update(
            {"id": "id_purchase_unit", "class": "form-control"}
        )
        self.fields["category"].widget.attrs.update(
            {"id": "id_category", "class": "form-control"}
        )

        for name, field in self.fields.items():
            if name in {"name", "base_unit", "purchase_unit", "category"}:
                continue
            if getattr(field.widget, "input_type", None) == "checkbox":
                field.widget.attrs.update({"class": "form-checkbox"})
            else:
                field.widget.attrs.update({"class": "form-control"})

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name", "")
        category = cleaned.get("category")
        base = cleaned.get("base_unit")
        purchase = cleaned.get("purchase_unit")
        if name and (not base or not purchase):
            inferred_base, inferred_purchase = infer_units(name, category)
            if not base and inferred_base:
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if getattr(field.widget, "input_type", None) == "checkbox":
                field.widget.attrs.update({"class": "form-checkbox"})
            else:
                field.widget.attrs.update({"class": "form-control"})


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


class IndentForm(forms.ModelForm):
    class Meta:
        model = Indent
        fields = ["requested_by", "department", "date_required", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if getattr(field.widget, "input_type", None) == "checkbox":
                field.widget.attrs.update({"class": "form-checkbox"})
            else:
                field.widget.attrs.update({"class": "form-control"})

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        if not obj.status:
            obj.status = "SUBMITTED"
        if commit:
            obj.save()
        return obj


class IndentItemForm(forms.ModelForm):
    class Meta:
        model = IndentItem
        fields = ["item", "requested_qty", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


IndentItemFormSet = forms.inlineformset_factory(
    Indent,
    IndentItem,
    form=IndentItemForm,
    fields=["item", "requested_qty", "notes"],
    extra=1,
    can_delete=True,
)


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            "supplier",
            "order_date",
            "expected_delivery_date",
            "status",
            "notes",
        ]


PurchaseOrderItemFormSet = forms.inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    fields=["item", "quantity_ordered", "unit_price"],
    extra=1,
    can_delete=True,
)


class GRNForm(forms.ModelForm):
    class Meta:
        model = GoodsReceivedNote
        fields = ["received_date", "notes"]


GRNItemFormSet = forms.inlineformset_factory(
    GoodsReceivedNote,
    GRNItem,
    fields=[
        "po_item",
        "quantity_ordered_on_po",
        "quantity_received",
        "unit_price_at_receipt",
        "item_notes",
    ],
    extra=0,
    can_delete=False,
)


class RecipeForm(forms.ModelForm):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if getattr(field.widget, "input_type", None) == "checkbox":
                field.widget.attrs.update({"class": "form-checkbox"})
            else:
                field.widget.attrs.update({"class": "form-control"})


class RecipeComponentForm(forms.ModelForm):
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
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


RecipeComponentFormSet = forms.inlineformset_factory(
    Recipe,
    RecipeComponent,
    form=RecipeComponentForm,
    fields=["component_kind", "component_id", "quantity", "unit", "loss_pct"],
    extra=1,
    can_delete=True,
)
