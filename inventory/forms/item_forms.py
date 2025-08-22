from __future__ import annotations

import logging
from django import forms
from django.urls import reverse

from ..models import Item, Category
from ..services.supabase_units import get_units
from .base import StyledFormMixin, INPUT_CLASS

logger = logging.getLogger(__name__)


class ItemForm(StyledFormMixin, forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(parent__isnull=True).order_by("name"),
        required=True,
        empty_label="---------",
    )
    sub_category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        empty_label="---------",
    )

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
            logger.warning("Failed to load units map", exc_info=True)
        self.units_map = units_map

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
        sub_field = self.fields["sub_category"]
        category_field.queryset = Category.objects.none()
        sub_field.queryset = Category.objects.none()
        selected_category = None
        try:
            category_field.queryset = Category.objects.filter(parent__isnull=True).order_by("name")
            selected_category = self.data.get("category")
            if not selected_category and self.instance.pk and self.instance.category:
                selected_category = (
                    Category.objects.filter(name=self.instance.category, parent__isnull=True)
                    .values_list("id", flat=True)
                    .first()
                )
                if selected_category:
                    category_field.initial = selected_category
            if selected_category:
                sub_field.queryset = (
                    Category.objects.filter(parent_id=selected_category).order_by("name")
                )
                if self.instance.pk and self.instance.sub_category:
                    sub_initial = (
                        Category.objects.filter(
                            name=self.instance.sub_category, parent_id=selected_category
                        )
                        .values_list("id", flat=True)
                        .first()
                    )
                    if sub_initial:
                        sub_field.initial = sub_initial
        except Exception:
            logger.warning("Failed to load categories", exc_info=True)
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
        sub_field.widget = forms.Select(
            attrs={"id": "id_sub_category", "class": INPUT_CLASS}
        )

        # Reapply styling for any widgets replaced above
        self.apply_styling()

    def save(self, commit: bool = True):
        obj = super().save(commit=False)
        category = self.cleaned_data.get("category")
        sub_category = self.cleaned_data.get("sub_category")
        if isinstance(category, Category):
            obj.category = category.name
        if isinstance(sub_category, Category):
            obj.sub_category = sub_category.name
        if commit:
            obj.save()
        return obj
