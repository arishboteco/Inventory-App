from __future__ import annotations

import logging

from django import forms

from ..models import Item
from ..services.supabase_categories import get_categories
from ..services.supabase_units import get_units
from .base import INPUT_CLASS, StyledFormMixin

logger = logging.getLogger(__name__)


class ItemForm(StyledFormMixin, forms.ModelForm):

    class Meta:
        model = Item
        fields = [
            "name",
            "base_unit",
            "purchase_unit",
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

        try:
            categories_map = get_categories()
            logger.debug("Categories map loaded: %s", categories_map)
        except Exception:
            categories_map = {}
            logger.error("Failed to load categories map", exc_info=True)
        self.categories_map = categories_map

        for field in ("name", "base_unit", "purchase_unit"):
            self.fields[field].required = True

        self.fields["name"].widget.attrs.update({"class": INPUT_CLASS})

        base_selected = self.data.get("base_unit") or self.initial.get("base_unit")
        logger.debug("Base unit selected: %s", base_selected)

        # Base unit field as text input with datalist
        base_field = self.fields["base_unit"]
        base_field.widget = forms.TextInput(
            attrs={
                "id": "id_base_unit",
                "class": INPUT_CLASS,
                "list": "base-unit-options",
            }
        )
        if base_selected:
            base_field.initial = base_selected

        # Purchase unit field with datalist options based on base unit
        purchase_field = self.fields["purchase_unit"]
        purchase_field.widget = forms.TextInput(
            attrs={
                "id": "id_purchase_unit",
                "class": INPUT_CLASS,
                "list": "purchase-unit-options",
            }
        )
        if self.data.get("purchase_unit"):
            purchase_field.initial = self.data.get("purchase_unit")
        elif self.initial.get("purchase_unit"):
            purchase_field.initial = self.initial.get("purchase_unit")

        # Build helper lists for template datalists
        self.base_units = sorted(units_map.keys())
        self.purchase_units = units_map.get(base_selected, [])

        # Category fields
        selected_category = self.data.get("category")
        selected_sub = self.data.get("sub_category")
        if not selected_category and self.instance and self.instance.category_id:
            cat_id = self.instance.category_id
            for cat in categories_map.get(None, []):
                if cat["id"] == cat_id:
                    selected_category = cat["name"]
                    break
            if not selected_category:
                for cat_name, subs in categories_map.items():
                    if cat_name is None:
                        continue
                    for sub in subs:
                        if sub["id"] == cat_id:
                            selected_category = cat_name
                            selected_sub = sub["name"]
                            break
                    if selected_category:
                        break

        self.fields["category"] = forms.CharField(
            required=False,
            widget=forms.TextInput(
                attrs={
                    "id": "id_category",
                    "class": INPUT_CLASS,
                    "list": "category-options",
                }
            ),
        )

        self.fields["sub_category"] = forms.CharField(
            required=False,
            widget=forms.TextInput(
                attrs={
                    "id": "id_sub_category",
                    "class": INPUT_CLASS,
                    "list": "sub-category-options",
                }
            ),
        )

        if selected_category:
            self.fields["category"].initial = selected_category
        if selected_sub:
            self.fields["sub_category"].initial = selected_sub

        # Lists for datalist population
        self.category_options = [c["name"] for c in categories_map.get(None, [])]
        self.sub_category_options = []
        if selected_category:
            self.sub_category_options = [
                c["name"] for c in categories_map.get(selected_category, [])
            ]

        if not self.instance.pk:
            self.fields["is_active"].initial = True

        # Reapply styling for any widgets replaced above
        self.apply_styling()

    def _resolve_category_id(self, category: str | None, sub_category: str | None):
        if sub_category:
            for sub in self.categories_map.get(category, []):
                if sub["name"] == sub_category:
                    return sub["id"]
        if category:
            for cat in self.categories_map.get(None, []):
                if cat["name"] == category:
                    return cat["id"]
        return None

    def save(self, commit: bool = True):
        cat_id = self._resolve_category_id(
            self.cleaned_data.get("category"),
            self.cleaned_data.get("sub_category"),
        )
        self.instance.category_id = cat_id
        return super().save(commit)
