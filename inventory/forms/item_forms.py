from django import forms

from ..models import Department, Item, Supplier, Unit
from ..services.categories_service import CategoriesService
from ..services.form_service import (
    get_categories_map,
    get_category_choices,
)
from ..services.units_service import BASE_UNIT_TO_UNIT_ID
from .base import INPUT_CLASS, StyledFormMixin


class ItemForm(StyledFormMixin, forms.ModelForm):
    """Enhanced item form with complete business field support."""

    # Category field using category_id foreign key
    category_id = forms.ChoiceField(
        choices=[],  # Will be populated in __init__
        required=False,
        help_text="Item category for classification",
        widget=forms.Select(
            attrs={
                "class": INPUT_CLASS,
                "data-field": "category_id",
                "placeholder": "Select category",
            }
        ),
    )

    # Department assignment with checkbox selection
    departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.all(),
        required=False,
        help_text="Departments that can use this item",
        widget=forms.CheckboxSelectMultiple(attrs={"class": "department-checkbox"}),
    )

    # Purchase and supplier information
    preferred_supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True),
        required=False,
        help_text="Default supplier for this item",
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )

    # Unit selection
    unit = forms.ModelChoiceField(
        queryset=Unit.objects.all(),
        empty_label=None,
        widget=forms.Select(attrs={"class": INPUT_CLASS, "data-field": "unit"}),
        help_text=(
            "Select the unit for this item (handles both kitchen and procurement units)"
        ),
    )

    class Meta:
        model = Item
        fields = [
            "name",
            "unit",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate category dropdown choices using proper service
        category_choices = [("", "Select Category")] + (
            CategoriesService.get_category_choices_for_forms()
        )
        self.fields["category_id"].choices = category_choices

        # Make name field required
        if "name" in self.fields:
            self.fields["name"].required = True

        # Set default unit
        if not self.instance.pk:
            default_unit = Unit.objects.filter(is_default=True).first()
            if default_unit:
                self.fields["unit"].initial = default_unit

        # Add data for JavaScript dropdowns (for categories)
        self.category_options = [choice[0] for choice in get_category_choices()]
        # Will be populated by JavaScript based on category
        self.sub_category_options = []

        # Add mapping data for JavaScript
        self.categories_map = get_categories_map()

        # Apply styling to all fields
        self.apply_styling()

    def clean(self):
        """Validate business rules and field relationships."""
        cleaned_data = super().clean()

        # Normalize blank category_id to None for DB compatibility
        if cleaned_data.get("category_id") in ("", None):
            cleaned_data["category_id"] = None

        base_unit = cleaned_data.get("base_unit")
        # purchase_unit kept for legacy compatibility; not used here
        _ = cleaned_data.get("purchase_unit")
        category = cleaned_data.get("category")
        sub_category = cleaned_data.get("sub_category")

        # Validate category-subcategory relationship
        if sub_category and not category:
            raise forms.ValidationError(
                "Category is required when subcategory is specified"
            )

        # Set unit based on base_unit for compatibility
        if base_unit and not cleaned_data.get("unit"):
            unit_id = BASE_UNIT_TO_UNIT_ID.get(base_unit, 55)
            cleaned_data["unit"] = Unit.objects.filter(pk=unit_id).first()

        return cleaned_data

    def save(self, commit=True):
        """Save the item with enhanced business logic."""
        instance = super().save(commit=False)

        # Update unit based on base_unit if needed
        if self.cleaned_data.get("base_unit") and not instance.unit_id:
            instance.unit_id = BASE_UNIT_TO_UNIT_ID.get(
                self.cleaned_data["base_unit"], 55
            )

        if commit:
            instance.save()
            # Save many-to-many relationships
            self.save_m2m()

        return instance

    def clean_unit(self):
        unit = self.cleaned_data.get("unit")
        if not unit or not Unit.objects.filter(pk=unit.pk).exists():
            raise forms.ValidationError(
                "Selected unit does not exist in units table."
            )
        return unit
