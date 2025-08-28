from django import forms
from ..models import Item, Department, Supplier
from ..services.form_service import (
    FormService, get_category_choices, get_subcategory_choices,
    get_categories_map, get_department_choices, get_supplier_choices
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
    
    # Category fields with proper dropdown support
    category = forms.ChoiceField(
        choices=[],  # Will be populated in __init__
        required=False,
        help_text="Item category for classification",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-field': 'category',
            'placeholder': 'Select category'
        })
    )
    
    sub_category = forms.ChoiceField(
        choices=[],  # Will be populated in __init__
        required=False,
        help_text="Item subcategory for detailed classification",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-field': 'sub_category',
            'placeholder': 'Select subcategory'
        })
    )
    
    # Department assignment with checkbox selection
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
        
        # Populate category dropdown choices
        category_choices = [('', 'Select Category')] + get_category_choices()
        self.fields['category'].choices = category_choices
        
        # Populate subcategory dropdown choices
        subcategory_choices = [('', 'Select Subcategory')] + get_subcategory_choices()
        self.fields['sub_category'].choices = subcategory_choices
        
        # Replace base_unit and purchase_unit fields with dropdown widgets
        self.fields['base_unit'] = forms.ChoiceField(
            choices=[('', 'Select Base Unit')] + FormService.get_base_unit_choices(),
            required=True,
            widget=forms.Select(attrs={
                'class': 'form-control',
                'data-field': 'base_unit'
            }),
            help_text="Primary unit for inventory tracking"
        )
        
        self.fields['purchase_unit'] = forms.ChoiceField(
            choices=[('', 'Select Purchase Unit')] + FormService.get_purchase_unit_choices(),
            required=False,
            widget=forms.Select(attrs={
                'class': 'form-control',
                'data-field': 'purchase_unit'
            }),
            help_text="Unit used when purchasing this item"
        )
        
        # Make name field required
        if "name" in self.fields:
            self.fields["name"].required = True
        
        # Set default unit_id for compatibility
        if not self.instance.pk and "unit_id" in self.fields:
            self.fields["unit_id"].initial = 55  # Default PC unit
        
        # Add data for JavaScript dropdowns (for categories)
        self.category_options = [choice[0] for choice in get_category_choices()]
        self.sub_category_options = []  # Will be populated by JavaScript based on category
        
        # Add mapping data for JavaScript
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
        
        # Validate category-subcategory relationship
        if sub_category and not category:
            raise forms.ValidationError("Category is required when subcategory is specified")
        
        # Set unit_id based on base_unit for compatibility
        if base_unit and not cleaned_data.get('unit_id'):
            # Map base units to unit_ids (you may need to adjust these mappings)
            unit_mapping = {
                'Kilograms': 19,
                'Liters': 1, 
                'Pieces': 55,
                'Boxes': 55,
                'Cases': 55,
                'Cartons': 55,
                'Grams': 19,
                'Milliliters': 1,
                'Units': 55,
                'Each': 55,
                'Packages': 55,
                'Bottles': 55,
                'Cans': 55,
            }
            cleaned_data['unit_id'] = unit_mapping.get(base_unit, 55)  # Default to PC
        
        return cleaned_data

    def save(self, commit=True):
        """Save the item with enhanced business logic."""
        instance = super().save(commit=False)
        
        # Update unit_id based on base_unit if needed
        if self.cleaned_data.get('base_unit') and not instance.unit_id:
            unit_mapping = {
                'Kilograms': 19,
                'Liters': 1,
                'Pieces': 55,
                'Boxes': 55, 
                'Packages': 55,
                'Units': 55,
                'Each': 55,
            }
            instance.unit_id = unit_mapping.get(self.cleaned_data['base_unit'], 55)
        
        if commit:
            instance.save()
            # Save many-to-many relationships
            self.save_m2m()
            
        return instance
