from __future__ import annotations

import logging
from django import forms

from ..models import Item
from ..services.supabase_units import get_units
from .base import StyledFormMixin, INPUT_CLASS

logger = logging.getLogger(__name__)


class ItemForm(StyledFormMixin, forms.ModelForm):

    class Meta:
        model = Item
        fields = [
            "name",
            "base_unit",
            "purchase_unit",
            "category_id",
            "permitted_departments",
            "reorder_point",
            "current_stock",
            "notes",
            "is_active",
        ]
        error_messages = {
            "name": {"required": "Item name is required."},
            "base_unit": {"required": "Base unit is required."},
            "purchase_unit": {"required": "Purchase unit is required."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            units_map = get_units()
            logger.debug("Units map loaded: %s", units_map)
        except Exception:
            units_map = {}
            logger.error("Failed to load units map", exc_info=True)
        self.units_map = units_map

        for field in ("name", "base_unit", "purchase_unit"):
            self.fields[field].required = True

        self.fields["name"].widget.attrs.update({"class": INPUT_CLASS})

        base_choices = [(u, u) for u in sorted(units_map.keys())]
        base_selected = self.data.get("base_unit") or self.initial.get("base_unit")
        logger.debug("Base unit selected: %s", base_selected)

        base_field = self.fields["base_unit"]
        base_field.choices = [("", "---------")] + base_choices
        base_field.widget = forms.Select(
            choices=base_field.choices,
            attrs={"id": "id_base_unit", "class": INPUT_CLASS},
        )
        if base_selected:
            base_field.initial = base_selected

        purchase_options = units_map.get(base_selected, [])
        logger.debug("Purchase options for %s: %s", base_selected, purchase_options)
        purchase_field = self.fields["purchase_unit"]
        purchase_field.choices = [("", "---------")] + [
            (u, u) for u in purchase_options
        ]
        purchase_field.widget = forms.Select(
            choices=purchase_field.choices,
            attrs={"id": "id_purchase_unit", "class": INPUT_CLASS},
        )
        if self.data.get("purchase_unit"):
            purchase_field.initial = self.data.get("purchase_unit")
        elif self.initial.get("purchase_unit"):
            purchase_field.initial = self.initial.get("purchase_unit")

        # Reapply styling for any widgets replaced above
        self.apply_styling()
