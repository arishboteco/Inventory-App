from decimal import Decimal

from django import forms
from django.forms.models import BaseInlineFormSet

from ..models import Item, Recipe, RecipeItem
from ..services.form_service import FormService
from .base import StyledFormMixin


def _match_base_unit(raw: str, choices: tuple[tuple[str, str], ...]) -> str | None:
    """Return canonical base_unit code from choices, or None if no match."""
    if not raw or not choices:
        return None
    r = str(raw).strip()
    for code, _label in choices:
        if str(code).strip().upper() == r.upper():
            return str(code).strip()
    return None


INPUT_CLASS = (
    "w-full px-3 py-2 text-sm border border-gray-300 rounded-lg "
    "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
)


class RecipeForm(StyledFormMixin, forms.ModelForm):
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS}),
        help_text="Unique recipe name",
    )
    description = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                "class": (
                    "h-4 w-4 text-blue-600 focus:ring-blue-500 "
                    "border-gray-300 rounded"
                )
            }
        ),
    )
    type = forms.ChoiceField(
        choices=Recipe.Type.choices,
        initial=Recipe.Type.FINAL,
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
        help_text="Final recipes are on the menu; Sub-recipes are components used inside other recipes.",
    )
    default_yield_qty = forms.DecimalField(
        required=False,
        initial=Decimal("1.0"),
        decimal_places=3,
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.001"}),
        help_text="Default quantity this recipe produces",
    )
    default_yield_unit = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.HiddenInput(),
        help_text="Unit for the yield quantity (sub-recipes only; finals use portion).",
    )
    plating_notes = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )
    description_and_plating = forms.CharField(
        required=False,
        label="Description & Plating Notes",
        widget=forms.Textarea(
            attrs={
                "class": INPUT_CLASS + " resize-y",
                "rows": 2,
                "style": "min-height: 2.75rem;",
                "placeholder": "Capture the story and plating cues for this recipe...",
            }
        ),
        help_text=(
            "Share the overview and plating details together so the team has a "
            "single reference."
        ),
    )
    # D2: Selling price and food cost target
    selling_price = forms.DecimalField(
        required=False,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "step": "0.01",
                "min": "0",
                "placeholder": "e.g. 25.00",
            }
        ),
        label="Menu Selling Price",
        help_text="Selling price excluding tax",
    )
    target_food_cost_pct = forms.DecimalField(
        required=False,
        decimal_places=2,
        initial=30.00,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "step": "0.1",
                "min": "0",
                "max": "100",
                "placeholder": "30.0",
            }
        ),
        label="Target Food Cost %",
        help_text="Target food cost as % of selling price (typically 28–32%)",
    )

    class Meta:
        model = Recipe
        fields = [
            "name",
            "description",
            "is_active",
            "type",
            "default_yield_qty",
            "default_yield_unit",
            "plating_notes",
            "selling_price",
            "target_food_cost_pct",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = tuple(FormService.get_base_unit_choices())
        self.sub_yield_unit_choices = choices

        description = self.initial.get("description") or getattr(
            self.instance, "description", ""
        )
        plating_notes = self.initial.get("plating_notes") or getattr(
            self.instance, "plating_notes", ""
        )
        if not self.is_bound:
            parts = [
                str(part).strip()
                for part in (description, plating_notes)
                if part and str(part).strip()
            ]
            combined = "\n\n".join(parts) if parts else ""
            if combined:
                self.initial.setdefault("description_and_plating", combined)
                self.fields["description_and_plating"].initial = combined

            eff_type = self._effective_recipe_type()
            raw_unit = (
                self.initial.get("default_yield_unit")
                or getattr(self.instance, "default_yield_unit", None)
                or ""
            )
            if eff_type == Recipe.Type.FINAL:
                self.initial["default_yield_unit"] = "portion"
                self.fields["default_yield_unit"].initial = "portion"
            else:
                matched = _match_base_unit(str(raw_unit), choices)
                pick = matched if matched else (choices[0][0] if choices else "")
                self.initial["default_yield_unit"] = pick
                self.fields["default_yield_unit"].initial = pick

    def _effective_recipe_type(self) -> str:
        if self.is_bound:
            raw = self.data.get(self.add_prefix("type"))
            if raw in (Recipe.Type.FINAL, Recipe.Type.SUB):
                return raw
        inst_type = getattr(self.instance, "type", None)
        if inst_type in (Recipe.Type.FINAL, Recipe.Type.SUB):
            return inst_type
        ini = self.initial.get("type")
        if ini in (Recipe.Type.FINAL, Recipe.Type.SUB):
            return ini
        return Recipe.Type.FINAL

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            return name
        duplicate_qs = Recipe.objects.filter(name=name)
        if self.instance and self.instance.pk:
            duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)
        if duplicate_qs.exists():
            raise forms.ValidationError("A recipe with this name already exists.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        combined = cleaned_data.get("description_and_plating", "")
        combined_text = str(combined).strip()
        cleaned_data["description"] = combined_text
        cleaned_data["plating_notes"] = combined_text

        recipe_type = cleaned_data.get("type")
        choices = tuple(FormService.get_base_unit_choices())

        if recipe_type == Recipe.Type.FINAL:
            cleaned_data["default_yield_unit"] = "portion"
        elif recipe_type == Recipe.Type.SUB:
            raw = (cleaned_data.get("default_yield_unit") or "").strip()
            canonical = _match_base_unit(raw, choices)
            if not canonical or not choices:
                self.add_error(
                    "default_yield_unit",
                    "Select a valid base unit for the yield.",
                )
            else:
                cleaned_data["default_yield_unit"] = canonical
        return cleaned_data


class IngredientSelect(forms.Select):
    """Select for encoded ingredient values (`i:<pk>` / `r:<pk>`) with kind markers."""

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        if value not in (None, ""):
            val = str(value)
            if val.startswith("i:"):
                option.setdefault("attrs", {})["data-ingredient-kind"] = "item"
            elif val.startswith("r:"):
                option.setdefault("attrs", {})["data-ingredient-kind"] = "sub"
        return option


class RecipeItemForm(StyledFormMixin, forms.ModelForm):
    """Single dropdown for inventory item or sub-recipe; maps to model FKs on save."""

    ingredient = forms.ChoiceField(
        required=False,
        choices=[],
        widget=IngredientSelect(
            attrs={
                "class": INPUT_CLASS + " predictive",
                "data-min-chars": "2",
                "data-placeholder": "Type 2+ chars to search ingredients",
            }
        ),
        label="Ingredient",
    )
    quantity = forms.DecimalField(
        required=False,
        min_value=0.01,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "step": "0.01",
                "min": "0.01",
                "placeholder": "0.00",
            }
        ),
        label="Quantity",
    )
    unit = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )
    unit_display = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "readonly": True,
                "placeholder": "Unit",
            }
        ),
        required=False,
        label="Unit",
    )
    loss_pct = forms.DecimalField(
        required=False,
        initial=0,
        min_value=0,
        max_value=100,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASS,
                "step": "0.01",
                "min": "0",
                "max": "100",
                "placeholder": "0.00",
            }
        ),
        label="Loss %",
    )

    class Meta:
        model = RecipeItem
        fields = [
            "quantity",
            "unit",
            "loss_pct",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        has_instance = getattr(instance, "pk", None) is not None
        unit_value = ""
        if has_instance:
            unit_value = instance.unit or ""
            if unit_value:
                self.initial.setdefault("unit", unit_value)
                self.initial.setdefault("unit_display", unit_value)
        self.fields["unit"].initial = self.initial.get("unit", unit_value)
        self.fields["unit_display"].initial = self.initial.get(
            "unit_display", unit_value
        )

        items_qs = Item.objects.filter(is_active=True).order_by("name")
        subs_qs = Recipe.objects.filter(is_active=True, type=Recipe.Type.SUB).order_by(
            "name"
        )
        parent_rid = getattr(instance, "recipe_id", None)
        if parent_rid:
            subs_qs = subs_qs.exclude(pk=parent_rid)

        item_choices = [(f"i:{obj.pk}", obj.name) for obj in items_qs]
        sub_choices = [(f"r:{obj.pk}", obj.name) for obj in subs_qs]

        choices: list = [("", "— Select ingredient —")]
        if item_choices:
            choices.append(("Inventory items", item_choices))
        if sub_choices:
            choices.append(("Sub-recipes", sub_choices))

        self.fields["ingredient"].choices = choices

        if has_instance:
            if instance.item_id:
                self.initial.setdefault("ingredient", f"i:{instance.item_id}")
            elif instance.sub_recipe_id:
                self.initial.setdefault("ingredient", f"r:{instance.sub_recipe_id}")

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["item"] = None
        cleaned_data["sub_recipe"] = None
        key = (cleaned_data.get("ingredient") or "").strip()
        if not key:
            qty = cleaned_data.get("quantity")
            if qty is not None:
                try:
                    if qty > 0:
                        self.add_error(
                            "ingredient",
                            "Select an ingredient or clear the quantity.",
                        )
                except (TypeError, ValueError):
                    pass
            return cleaned_data
        try:
            if key.startswith("i:"):
                pk = int(key[2:], 10)
                item = Item.objects.get(pk=pk, is_active=True)
                cleaned_data["item"] = item
            elif key.startswith("r:"):
                pk = int(key[2:], 10)
                sub = Recipe.objects.get(pk=pk, is_active=True, type=Recipe.Type.SUB)
                parent_rid = getattr(self.instance, "recipe_id", None)
                if parent_rid and pk == parent_rid:
                    self.add_error(
                        "ingredient",
                        "A recipe cannot use itself as an ingredient.",
                    )
                    return cleaned_data
                cleaned_data["sub_recipe"] = sub
            else:
                self.add_error("ingredient", "Select a valid ingredient.")
                return cleaned_data
        except (ValueError, Item.DoesNotExist, Recipe.DoesNotExist):
            self.add_error("ingredient", "Select a valid ingredient.")
            return cleaned_data
        return cleaned_data

    def _post_clean(self):
        if self.cleaned_data.get("DELETE"):
            super()._post_clean()
            return
        ingredient = (self.cleaned_data.get("ingredient") or "").strip()
        item_obj = self.cleaned_data.get("item")
        sub_obj = self.cleaned_data.get("sub_recipe")
        if not ingredient and not item_obj and not sub_obj:
            # Blank formset row: skip RecipeItem.clean() (FKs still null on instance).
            return
        self.instance.item = item_obj
        self.instance.sub_recipe = sub_obj
        super()._post_clean()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.item = self.cleaned_data.get("item")
        instance.sub_recipe = self.cleaned_data.get("sub_recipe")
        if commit:
            instance.save()
        return instance


class BaseRecipeItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        has_positive_ingredient = False
        for form in self.forms:
            cleaned = getattr(form, "cleaned_data", {})
            if not cleaned or cleaned.get("DELETE"):
                continue
            has_ingredient = bool(cleaned.get("item") or cleaned.get("sub_recipe"))
            quantity = cleaned.get("quantity")
            if has_ingredient and quantity is not None and quantity > 0:
                has_positive_ingredient = True
                break

        if not has_positive_ingredient:
            raise forms.ValidationError(
                "Add at least one ingredient with a positive quantity."
            )


RecipeItemFormSet = forms.inlineformset_factory(
    Recipe,
    RecipeItem,
    form=RecipeItemForm,
    formset=BaseRecipeItemFormSet,
    fk_name="recipe",
    fields=["ingredient", "quantity", "unit", "loss_pct"],
    extra=1,
    can_delete=True,
)

RecipeItemEditFormSet = forms.inlineformset_factory(
    Recipe,
    RecipeItem,
    form=RecipeItemForm,
    formset=BaseRecipeItemFormSet,
    fk_name="recipe",
    fields=["ingredient", "quantity", "unit", "loss_pct"],
    extra=0,
    can_delete=True,
)
