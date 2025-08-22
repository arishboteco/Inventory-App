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
            "notes",
            "is_active",
        ]
