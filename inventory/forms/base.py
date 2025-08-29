from __future__ import annotations

from django import forms

INPUT_CLASS = "w-full px-3 py-2 border rounded"
CHECKBOX_CLASS = "h-4 w-4 text-primary"


class StyledFormMixin:
    """Apply Tailwind CSS classes and predictive selects to form fields.

    - Appends INPUT_CLASS to all non-checkbox inputs.
    - Appends CHECKBOX_CLASS to checkbox inputs.
    - Appends 'predictive' to Select/SelectMultiple widgets for JS enhancement.
    - Preserves any existing CSS classes on widgets.
    """

    def _append_class(self, widget: forms.Widget, *classes: str) -> None:
        existing = (widget.attrs.get("class") or "").split()
        for cls in classes:
            if cls and cls not in existing:
                existing.append(cls)
        widget.attrs["class"] = " ".join(c for c in existing if c)

    def apply_styling(self) -> None:
        for field in self.fields.values():
            widget = field.widget
            # Checkbox inputs
            if getattr(widget, "input_type", None) == "checkbox":
                self._append_class(widget, CHECKBOX_CLASS)
                continue

            # All other inputs get the base INPUT_CLASS
            self._append_class(widget, INPUT_CLASS)

            # Predictive selects
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                self._append_class(widget, "predictive")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()
