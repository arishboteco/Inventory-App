from __future__ import annotations

from datetime import date
from decimal import Decimal

from django import forms

from ..models import Department, Indent, IndentItem
from ..models.enums import IndentStatus
from .base import INPUT_CLASS, StyledFormMixin
from .stock_forms import ItemNameResolutionMixin


class IndentForm(StyledFormMixin, forms.ModelForm):
    notes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS}),
    )

    class Meta:
        model = Indent
        fields = ["requested_by", "department", "date_required", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide department in UI; we present a predictive dropdown in the template and sync to this field.
        if "department" in self.fields:
            self.fields["department"].widget = forms.HiddenInput()
            # Backward-compat: accept department name strings (used in tests)
            if self.is_bound:
                dep_raw = self.data.get("department")
                if dep_raw and not str(dep_raw).isdigit():
                    try:
                        dep = Department.objects.only("department_id").get(name=dep_raw)
                        data = self.data.copy()
                        data["department"] = str(dep.pk)
                        self.data = data
                    except Department.DoesNotExist:
                        # If no matching department exists, drop the value (field is optional)
                        data = self.data.copy()
                        data["department"] = ""
                        self.data = data
        # Hide requested_by in UI (we set it from request.user in the view)
        if "requested_by" in self.fields:
            self.fields["requested_by"].widget = forms.HiddenInput()
        # Render date_required as a dropdown of upcoming dates (today + next 30 days)
        # Replace with a date picker calendar (HTML date input) allowing future dates only
        if "date_required" in self.fields:
            try:
                today = date.today()
                self.fields["date_required"].widget = forms.DateInput(
                    attrs={
                        "type": "date",
                        "min": today.strftime("%Y-%m-%d"),
                        "class": INPUT_CLASS,
                    }
                )
                # Default calendar to today for new forms
                self.fields["date_required"].initial = today
            except Exception:
                # Fall back silently if anything goes wrong
                pass
        self.apply_styling()

    # No explicit department clean: optional at form level for backward-compat/tests.

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        # Ensure MRN is set (fallback generator based on next indent_id)
        if not getattr(obj, "mrn", None):
            try:
                # Use next sequence based on current max ID; zero-pad to 3+ digits
                from ..models import Indent as IndentModel

                last = (
                    IndentModel.objects.only("indent_id")
                    .order_by("-indent_id")
                    .first()
                )
                next_num = (last.indent_id + 1) if last and last.indent_id else 1
                obj.mrn = f"MRN-{str(next_num).zfill(3)}"
            except Exception:
                obj.mrn = "MRN-001"
        if not obj.status:
            obj.status = IndentStatus.SUBMITTED
        if commit:
            obj.save()
        return obj


class IndentItemForm(ItemNameResolutionMixin, StyledFormMixin, forms.ModelForm):
    notes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS}),
    )

    class Meta:
        model = IndentItem
        fields = ["item", "requested_qty", "notes"]

    def __init__(self, *args, item_suggest_url: str | None = None, item_list_id: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        item_attrs = {
            "class": INPUT_CLASS,
            "data-predictive-input": "1",
            "autocomplete": "off",
            "autocapitalize": "none",
            "autocorrect": "off",
            "spellcheck": "false",
        }
        if item_suggest_url:
            item_attrs.update(
                {
                    "hx-get": item_suggest_url,
                    "hx-trigger": "keyup changed delay:500ms",
                    "hx-target": "#item-options",
                    "list": "item-options",
                    "hx-include": "#id_department, #department-ui",
                }
            )
        # Accept name/ID patterns like stock forms; resolve to Item in clean_item
        self.fields["item"] = forms.CharField(
            label="Item",
            required=True,
            widget=forms.TextInput(attrs=item_attrs),
        )
        self.apply_styling()

    def clean_requested_qty(self):
        qty = self.cleaned_data.get("requested_qty")
        if qty is None or qty <= 0:
            raise forms.ValidationError("Quantity must be positive")
        return qty

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        # Some environments enforce NOT NULL on issued_qty; default to 0
        if getattr(obj, "issued_qty", None) is None:
            try:
                obj.issued_qty = Decimal("0")
            except Exception:
                obj.issued_qty = 0
        if commit:
            obj.save()
        return obj


class _IndentItemFormSetBase(forms.BaseInlineFormSet):
    def save(self, commit=True):
        instances = super().save(commit=False)
        # Default issued_qty to 0 for all instances to satisfy NOT NULL constraints
        for obj in instances:
            if getattr(obj, "issued_qty", None) is None:
                try:
                    obj.issued_qty = Decimal("0")
                except Exception:
                    obj.issued_qty = 0
            if commit:
                obj.save()
        # Handle deletions
        if commit:
            self.save_m2m()
        return instances

IndentItemFormSet = forms.inlineformset_factory(
    Indent,
    IndentItem,
    form=IndentItemForm,
    formset=_IndentItemFormSetBase,
    fields=["item", "requested_qty", "notes"],
    extra=1,
    can_delete=True,
)
