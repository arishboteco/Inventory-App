from __future__ import annotations

INPUT_CLASS = "w-full px-3 py-2 border rounded"
CHECKBOX_CLASS = "h-4 w-4 text-blue-600"


class StyledFormMixin:
    """Apply Tailwind CSS classes to form fields."""

    def apply_styling(self) -> None:
        for field in self.fields.values():
            if getattr(field.widget, "input_type", None) == "checkbox":
                field.widget.attrs.update({"class": CHECKBOX_CLASS})
            else:
                field.widget.attrs.update({"class": INPUT_CLASS})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()
