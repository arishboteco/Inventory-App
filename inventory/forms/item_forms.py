from __future__ import annotations

import logging
from django import forms
from django.urls import reverse

from ..models import Item, Category
from ..services.supabase_units import get_units
from ..services.supabase_categories import get_categories
from .base import StyledFormMixin, INPUT_CLASS

logger = logging.getLogger(__name__)


class ItemForm(StyledFormMixin, forms.ModelForm):
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=True)
    sub_category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False)

    class Meta:
        model = Item
        fields = [
            "name",
            "base_unit",
            "purchase_unit",
            "category",
            "sub_category",
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
            "category": {"required": "Category is required."},
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

        for field in ("name", "base_unit", "purchase_unit", "category"):
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

        category_field = self.fields["category"]
        top_categories = categories_map.get(None, [])
        top_ids = [cat["id"] for cat in top_categories]
        category_field.queryset = Category.objects.filter(id__in=top_ids)
        category_field.empty_label = "---------"
        category_field.widget = forms.Select(
            attrs={
                "id": "id_category",
                "class": INPUT_CLASS,
                "hx-get": reverse("item_subcategory_options"),
                "hx-trigger": "change",
                "hx-target": "#id_sub_category",
                "hx-swap": "innerHTML",
            }
        )

        sub_field = self.fields["sub_category"]
        selected_category = self.data.get("category")
        if not selected_category and self.instance.pk and self.instance.category_id:
            selected_category = str(self.instance.category_id)
            category_field.initial = self.instance.category
        if selected_category:
            subcats = categories_map.get(int(selected_category), [])
            sub_ids = [cat["id"] for cat in subcats]
            sub_field.queryset = Category.objects.filter(id__in=sub_ids)
        else:
            sub_field.queryset = Category.objects.none()
        sub_field.empty_label = "---------"
        sub_field.widget = forms.Select(
            attrs={"id": "id_sub_category", "class": INPUT_CLASS}
        )
        if self.instance.pk and self.instance.sub_category_id:
            sub_field.initial = self.instance.sub_category

        # Reapply styling for any widgets replaced above
        self.apply_styling()

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        obj.category = self.cleaned_data.get("category")
        obj.sub_category = self.cleaned_data.get("sub_category")
        if commit:
            obj.save()
        return obj
