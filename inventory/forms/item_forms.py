from django import forms
from ..models import Item, Department, Supplier
from ..services.form_service import (
    get_unit_choices, get_units_map, get_category_choices, 
    get_categories_map, get_department_choices, get_supplier_choices,
    get_purchase_unit_choices
)

INPUT_CLASS = "form-input"


class StyledFormMixin:
    """Mixin to add consistent styling to forms."""
    
    def apply_styling(self):
        """Apply consistent styling to all form fields."""
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                field.widget.attrs.update({'class': INPUT_CLASS})


class ItemForm(StyledFormMixin, forms.ModelForm):
    """Enhanced item form with complete business field support."""
    
    # Unit fields with dropdown support
    base_unit = forms.CharField(
        max_length=50,
        required=False,
        help_text="Base unit of measurement (kg, ltr, pc, etc.)",
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'list': 'base-unit-options',
            'placeholder': 'Select or type base unit'
        })
    )
    
    purchase_unit = forms.CharField(
        max_length=50,
        required=False,
        help_text="Unit used for purchasing (g, ml, each, etc.)",
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'list': 'purchase-unit-options',
            'placeholder': 'Select or type purchase unit'
        })
    )
    
    # Category fields with dropdown support
    category = forms.CharField(
        max_length=100,
        required=False,
        help_text="Item category for classification",
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'list': 'category-options',
            'placeholder': 'Select or type category'
        })
    )
    
    sub_category = forms.CharField(
        max_length=100,
        required=False,
        help_text="Item subcategory for detailed classification",
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'list': 'sub-category-options',
            'placeholder': 'Select or type subcategory'
        })
    )
    
    # Department assignment
    departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.all(),
        required=False,
        help_text="Departments that can use this item",
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'department-checkbox'})
    )
    
    # Purchase and supplier information
    preferred_supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True),
        required=False,
        help_text="Default supplier for this item",
        widget=forms.Select(attrs={'class': INPUT_CLASS})
    )

    class Meta:
        model = Item
        fields = [
            "name",
            "base_unit",
            "purchase_unit", 
            "category",
            "sub_category",
            "departments",
            "initial_purchase_price",
            "preferred_supplier",
            "minimum_order_qty",
            "lead_time_days",
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
            'initial_purchase_price': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'minimum_order_qty': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'step': '0.01',
                'min': '0',
                'placeholder': '1.00'
            }),
            'lead_time_days': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'min': '0',
                'placeholder': '7'
            }),
            'unit_id': forms.HiddenInput(),  # Keep for compatibility but hide
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
        
        # Make name field required
        if "name" in self.fields:
            self.fields["name"].required = True
        
        # Set default unit_id for compatibility
        if not self.instance.pk and "unit_id" in self.fields:
            self.fields["unit_id"].initial = 55  # Default PC unit
        
        # Add data for JavaScript dropdowns
        self.base_units = [choice[0] for choice in get_unit_choices()]
        self.purchase_units = []  # Will be populated by JavaScript based on base_unit
        self.category_options = [choice[0] for choice in get_category_choices()]
        self.sub_category_options = []  # Will be populated by JavaScript based on category
        
        # Add mapping data for JavaScript
        self.units_map = get_units_map()
        self.categories_map = get_categories_map()
        
        # Apply styling to all fields
        self.apply_styling()

    def clean(self):
        """Validate business rules and field relationships."""
        cleaned_data = super().clean()
        
        base_unit = cleaned_data.get('base_unit')
        purchase_unit = cleaned_data.get('purchase_unit')
        category = cleaned_data.get('category')
        sub_category = cleaned_data.get('sub_category')
        
        # Validate unit relationship
        if base_unit and purchase_unit:
            valid_purchase_units = [choice[0] for choice in get_purchase_unit_choices(base_unit)]
            if purchase_unit not in valid_purchase_units:
                raise forms.ValidationError(
                    f"Purchase unit '{purchase_unit}' is not valid for base unit '{base_unit}'"
                )
        
        # Validate category-subcategory relationship
        if sub_category and not category:
            raise forms.ValidationError("Category is required when subcategory is specified")
        
        # Set unit_id based on base_unit for compatibility
        if base_unit and not cleaned_data.get('unit_id'):
            # Map base units to unit_ids (you may need to adjust these mappings)
            unit_mapping = {
                'kg': 19,
                'ltr': 1, 
                'pc': 55,
                'box': 55,
                'pack': 55,
            }
            cleaned_data['unit_id'] = unit_mapping.get(base_unit, 55)
        
        return cleaned_data

    def save(self, commit=True):
        """Save the item with enhanced business logic."""
        instance = super().save(commit=False)
        
        # Update unit_id based on base_unit if needed
        if self.cleaned_data.get('base_unit') and not instance.unit_id:
            unit_mapping = {
                'kg': 19,
                'ltr': 1,
                'pc': 55,
                'box': 55, 
                'pack': 55,
            }
            instance.unit_id = unit_mapping.get(self.cleaned_data['base_unit'], 55)
        
        if commit:
            instance.save()
            # Save many-to-many relationships
            self.save_m2m()
            
        return instance
