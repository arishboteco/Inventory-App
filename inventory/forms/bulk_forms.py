from django import forms


class BulkUploadForm(forms.Form):
    file = forms.FileField()


class BulkDeleteForm(forms.Form):
    file = forms.FileField()
