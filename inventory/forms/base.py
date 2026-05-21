from __future__ import annotations

from django import forms

DATE_INPUT_FORMATS_FALLBACK = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%m-%d-%Y",
)
TIME_INPUT_FORMATS_FALLBACK = ("%H:%M", "%H:%M:%S")

INPUT_CLASS = (
    "block w-full p-2 border border-form-border rounded-md bg-form-bg text-form-text "
    "focus:outline-none focus:ring-2 focus:ring-primary"
)
CHECKBOX_CLASS = "h-4 w-4 rounded border-form-border text-primary focus:ring-primary"


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

            # Ensure native pickers for date/time widgets unless explicitly overridden
            if isinstance(widget, forms.DateInput) and "type" not in widget.attrs:
                widget.input_type = "date"
                widget.attrs["type"] = "date"
                if not getattr(widget, "format", None):
                    widget.format = "%Y-%m-%d"
            elif isinstance(widget, forms.DateTimeInput) and "type" not in widget.attrs:
                widget.input_type = "datetime-local"
                widget.attrs["type"] = "datetime-local"
            elif isinstance(widget, forms.TimeInput) and "type" not in widget.attrs:
                widget.input_type = "time"
                widget.attrs["type"] = "time"
                if not getattr(widget, "format", None):
                    widget.format = "%H:%M"

            # Accept common manual text formats in addition to native picker values.
            if isinstance(field, forms.DateField):
                existing = tuple(getattr(field, "input_formats", ()) or ())
                field.input_formats = tuple(
                    dict.fromkeys((*DATE_INPUT_FORMATS_FALLBACK, *existing))
                )
            elif isinstance(field, forms.TimeField):
                existing = tuple(getattr(field, "input_formats", ()) or ())
                field.input_formats = tuple(
                    dict.fromkeys((*TIME_INPUT_FORMATS_FALLBACK, *existing))
                )

            # All other inputs get the base INPUT_CLASS
            self._append_class(widget, INPUT_CLASS)

            # Predictive selects
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                self._append_class(widget, "predictive")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()
