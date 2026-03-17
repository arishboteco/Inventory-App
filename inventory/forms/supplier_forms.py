from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from ..models import PAYMENT_TERMS_CHOICES, Supplier
from .base import INPUT_CLASS, StyledFormMixin


class SupplierForm(StyledFormMixin, forms.ModelForm):
    supplier_rating = forms.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "min": "1",
                "max": "5",
                "placeholder": "1–5",
                "aria-label": "Supplier rating",
            }
        ),
        help_text="Rate 1 (poor) to 5 (excellent)",
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": INPUT_CLASS,
                "rows": 3,
                "placeholder": "Additional notes about this supplier",
                "aria-label": "Notes",
            }
        ),
    )

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
            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Enter supplier name",
                    "aria-label": "Supplier name",
                }
            ),
            "contact_person": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Primary contact person",
                    "aria-label": "Contact person",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "+1 (555) 123-4567",
                    "aria-label": "Phone number",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "supplier@company.com",
                    "aria-label": "Email address",
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": INPUT_CLASS,
                    "rows": 3,
                    "placeholder": "Full business address",
                    "aria-label": "Address",
                }
            ),
            "tax_id": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Tax ID / EIN",
                    "aria-label": "Tax ID",
                }
            ),
            "payment_terms": forms.Select(
                choices=[("", "— Select —")] + PAYMENT_TERMS_CHOICES,
                attrs={
                    "class": INPUT_CLASS,
                    "aria-label": "Payment terms",
                }
            ),
            "credit_limit": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "0.00",
                    "aria-label": "Credit limit",
                }
            ),
            # Let StyledFormMixin add checkbox classes
            "is_active": forms.CheckboxInput(),
        }

    def clean_supplier_rating(self):
        """Validate supplier rating is between 1 and 5."""
        rating = self.cleaned_data.get("supplier_rating")
        if rating is not None and (rating < 1 or rating > 5):
            raise forms.ValidationError("Supplier rating must be between 1 and 5")
        return rating
