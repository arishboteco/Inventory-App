from django import forms

from ..models import Category, Department, Item, Supplier, Unit
from .base import INPUT_CLASS, StyledFormMixin


class ItemForm(StyledFormMixin, forms.ModelForm):
    """Item form using service-backed foreign key fields."""

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": INPUT_CLASS,
                "rows": 3,
                "placeholder": "Additional notes about this item",
            }
        ),
    )

    category_id = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        to_field_name="category_id",
        empty_label="Select Category",
        help_text="Item category for classification",
        widget=forms.Select(
            attrs={
                "class": INPUT_CLASS,
                "data-field": "category_id",
                "placeholder": "Select category",
            }
        ),
    )

    unit_id = forms.ModelChoiceField(
        queryset=Unit.objects.none(),
        required=True,
        to_field_name="unit_id",
        empty_label="Select Unit",
        help_text=(
            "Select the unit for this item (handles both kitchen and procurement units)"
        ),
        widget=forms.Select(attrs={"class": INPUT_CLASS, "data-field": "unit_id"}),
    )

    departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.all(),
        required=False,
        help_text="Departments that can use this item",
        widget=forms.CheckboxSelectMultiple(attrs={"class": "department-checkbox"}),
    )

    preferred_supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True),
        required=False,
        help_text="Default supplier for this item",
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )

    class Meta:
        model = Item
        fields = [
            "name",
            "unit_id",
            "category_id",
            "departments",
            "initial_purchase_price",
            "preferred_supplier",
            "minimum_order_qty",
            "lead_time_days",
            "reorder_point",
            "current_stock",
            "notes",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Enter item name"}
            ),
            "initial_purchase_price": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "0.00",
                }
            ),
            "minimum_order_qty": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "1.00",
                }
            ),
            "lead_time_days": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "min": "0", "placeholder": "7"}
            ),
            "unit_id": forms.Select(
                attrs={"class": INPUT_CLASS, "data-field": "unit_id"}
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
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": (
                        "h-4 w-4 rounded border-gray-300 "
                        "text-primary focus:ring-primary"
                    )
                },
            ),
        }
        error_messages = {
            "name": {"required": "Item name is required."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate dropdown querysets via ORM
        self.fields["unit_id"].queryset = Unit.objects.all().order_by(
            "base_unit", "purchase_unit"
        )
        self.fields["category_id"].queryset = Category.objects.all().order_by(
            "category", "sub_category"
        )

        if "name" in self.fields:
            self.fields["name"].required = True

        if self.instance.pk:
            self.fields["unit_id"].initial = self.instance.unit_id
            if self.instance.category_id:
                self.fields["category_id"].initial = self.instance.category_id
        else:
            self.fields["unit_id"].initial = 55

        self.apply_styling()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.unit = self.cleaned_data["unit_id"]
        instance.category = self.cleaned_data.get("category_id")
        if commit:
            instance.save()
            self.save_m2m()
        return instance
