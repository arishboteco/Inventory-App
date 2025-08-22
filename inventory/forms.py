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
from .services.supabase_units import get_units


INPUT_CLASS = "w-full px-3 py-2 border rounded"
CHECKBOX_CLASS = "h-4 w-4 text-blue-600"


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        units_map = get_units()
        self.units_map = units_map

        for field in ("name", "base_unit", "purchase_unit", "category"):
            self.fields[field].required = True

        self.fields["name"].widget.attrs.update({"class": INPUT_CLASS})

        base_choices = [(u, u) for u in sorted(units_map.keys())]
        base_selected = self.data.get("base_unit") or self.initial.get("base_unit")

        base_field = self.fields["base_unit"]
        base_field.choices = [("", "---------")] + base_choices
        base_field.widget = forms.Select(
            choices=base_field.choices,
            attrs={"id": "id_base_unit", "class": INPUT_CLASS},
        )
        if base_selected:
            base_field.initial = base_selected

        purchase_options = units_map.get(base_selected, [])
        purchase_field = self.fields["purchase_unit"]
        purchase_field.choices = [("", "---------")] + [
            (u, u) for u in purchase_options
        ]
        purchase_field.widget = forms.Select(
            choices=purchase_field.choices,
            attrs={"id": "id_purchase_unit", "class": INPUT_CLASS},
        )
        if self.data.get("purchase_unit"):
            purchase_field.initial = self.data.get("purchase_unit")
        elif self.initial.get("purchase_unit"):
            purchase_field.initial = self.initial.get("purchase_unit")

        self.fields["category"].widget.attrs.update(
            {"id": "id_category", "class": INPUT_CLASS}
        )

        for name, field in self.fields.items():
            if name in {"name", "base_unit", "purchase_unit", "category"}:
                continue
            if getattr(field.widget, "input_type", None) == "checkbox":
                field.widget.attrs.update({"class": CHECKBOX_CLASS})
            else:
                field.widget.attrs.update({"class": INPUT_CLASS})



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
                field.widget.attrs.update({"class": CHECKBOX_CLASS})
            else:
                field.widget.attrs.update({"class": INPUT_CLASS})


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
                field.widget.attrs.update({"class": CHECKBOX_CLASS})
            else:
                field.widget.attrs.update({"class": INPUT_CLASS})

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

    def __init__(self, *args, item_suggest_url: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        item_attrs = {"class": INPUT_CLASS}
        if item_suggest_url:
            item_attrs.update(
                {
                    "hx-get": item_suggest_url,
                    "hx-trigger": "keyup changed delay:500ms",
                    "hx-target": "#item-options",
                    "list": "item-options",
                }
            )
        self.fields["item"].widget = forms.TextInput()
        self.fields["item"].widget.attrs.update(item_attrs)
        for name, field in self.fields.items():
            if name == "item":
                continue
            field.widget.attrs.update({"class": INPUT_CLASS})


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

    def __init__(self, *args, supplier_suggest_url: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        supplier_attrs = {"class": INPUT_CLASS}
        if supplier_suggest_url:
            supplier_attrs.update(
                {
                    "hx-get": supplier_suggest_url,
                    "hx-trigger": "keyup changed delay:500ms",
                    "hx-target": "#supplier-options",
                    "list": "supplier-options",
                }
            )
        self.fields["supplier"].widget = forms.TextInput()
        self.fields["supplier"].widget.attrs.update(supplier_attrs)
        for name, field in self.fields.items():
            if name == "supplier":
                continue
            field.widget.attrs.update({"class": INPUT_CLASS})


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ["item", "quantity_ordered", "unit_price"]

    def __init__(self, *args, item_suggest_url: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        item_attrs = {"class": INPUT_CLASS}
        if item_suggest_url:
            item_attrs.update(
                {
                    "hx-get": item_suggest_url,
                    "hx-trigger": "keyup changed delay:500ms",
                    "hx-target": "#item-options",
                    "list": "item-options",
                }
            )
        self.fields["item"].widget = forms.TextInput()
        self.fields["item"].widget.attrs.update(item_attrs)
        for name, field in self.fields.items():
            if name == "item":
                continue
            field.widget.attrs.update({"class": INPUT_CLASS})


PurchaseOrderItemFormSet = forms.inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
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
                field.widget.attrs.update({"class": CHECKBOX_CLASS})
            else:
                field.widget.attrs.update({"class": INPUT_CLASS})


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
            field.widget.attrs.update({"class": INPUT_CLASS})


RecipeComponentFormSet = forms.inlineformset_factory(
    Recipe,
    RecipeComponent,
    form=RecipeComponentForm,
    fields=["component_kind", "component_id", "quantity", "unit", "loss_pct"],
    extra=1,
    can_delete=True,
)
