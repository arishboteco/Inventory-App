from django import forms

from .base import StyledFormMixin


class BulkUploadForm(StyledFormMixin, forms.Form):
    file = forms.FileField()


class BulkDeleteForm(StyledFormMixin, forms.Form):
    file = forms.FileField()
