from __future__ import annotations

from django import forms

INPUT_CLASS = "w-full px-3 py-2 border rounded"
CHECKBOX_CLASS = "h-4 w-4 text-primary"


class StyledFormMixin:
    """Apply Tailwind CSS classes to form fields."""

    def apply_styling(self) -> None:
        for field in self.fields.values():
            widget = field.widget
            if getattr(widget, "input_type", None) == "checkbox":
                widget.attrs.update({"class": CHECKBOX_CLASS})
            else:
                classes = INPUT_CLASS
                # Standard dropdown styling - no predictive class for cleaner appearance
                widget.attrs.update({"class": classes})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()
