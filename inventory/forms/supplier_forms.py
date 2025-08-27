from django import forms

from ..models import Supplier
from .base import StyledFormMixin


class SupplierForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "name",
            "contact_person",
            "phone",
            "email",
            "address",
            "tax_id",
            "payment_terms",
            "credit_limit",
            "supplier_rating",
            "notes",
            "is_active",
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter supplier name'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Primary contact person'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+1 (555) 123-4567'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'supplier@company.com'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Full business address'
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Tax ID / EIN'
            }),
            'payment_terms': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Net 30, COD, etc.'
            }),
            'credit_limit': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '10000.00'
            }),
            'supplier_rating': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '5',
                'placeholder': '5'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Additional notes about this supplier'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'})
        }

    def clean_supplier_rating(self):
        """Validate supplier rating is between 1 and 5."""
        rating = self.cleaned_data.get('supplier_rating')
        if rating is not None and (rating < 1 or rating > 5):
            raise forms.ValidationError("Supplier rating must be between 1 and 5")
        return rating
