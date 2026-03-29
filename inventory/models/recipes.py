from decimal import Decimal

from django.db import models

from .fields import CoerceFloatField


class Recipe(models.Model):
    class Type(models.TextChoices):
        FINAL = "FINAL", "Final Recipe"
        SUB = "SUB", "Sub-Recipe"

    recipe_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, null=False, blank=False)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=False, null=False)
    type = models.CharField(
        max_length=10,
        choices=Type.choices,
        default=Type.FINAL,
        null=False,
        blank=False,
    )
    default_yield_qty = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    default_yield_unit = models.CharField(max_length=50, blank=True, null=True)
    plating_notes = models.TextField(blank=True, null=True, default="")
    tags = models.JSONField(default=list, blank=True, null=True)
    version = models.IntegerField(blank=True, null=True)
    effective_from = models.DateField(auto_now_add=True)
    effective_to = models.DateField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # D2: Selling price and food cost tracking
    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Menu selling price (ex. tax)",
    )
    target_food_cost_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=30.00,
        help_text="Target food cost percentage for this item type",
    )

    def __str__(self):
        return self.name or f"Recipe {self.pk}"

    def get_total_cost(self, _visited=None):
        """Calculate total cost using last/initial purchase price.

        Uses a visited set to prevent infinite loops from circular sub-recipe
        references (added in D1).
        """
        if _visited is None:
            _visited = set()
        if self.pk in _visited:
            return Decimal("0")
        _visited.add(self.pk)

        total = Decimal("0")
        for recipe_item in self.items.select_related("item", "sub_recipe").all():
            # Sub-recipe support (D1): check attribute exists and is set
            sub = getattr(recipe_item, "sub_recipe", None)
            if sub is not None:
                sub_cost = sub.get_total_cost(_visited=_visited.copy())
                sub_yield = Decimal(str(sub.default_yield_qty or 1)) or Decimal("1")
                qty = Decimal(str(recipe_item.quantity or 0))
                loss_mult = Decimal("1") + (
                    Decimal(str(recipe_item.loss_pct or 0)) / Decimal("100")
                )
                if sub_yield:
                    total += (sub_cost / sub_yield) * qty * loss_mult
            elif recipe_item.item:
                from inventory.services.units_service import UnitsService

                item = recipe_item.item
                cost_per_base = UnitsService.cost_per_base_for_item(item)
                qty = Decimal(str(recipe_item.quantity or 0))
                loss_pct = Decimal(str(recipe_item.loss_pct or 0))
                if qty and loss_pct and loss_pct < 100:
                    try:
                        effective_qty = qty / (1 - loss_pct / 100)
                    except (ArithmeticError, ZeroDivisionError):
                        effective_qty = qty
                else:
                    effective_qty = qty
                total += cost_per_base * effective_qty
        return total

    @property
    def food_cost_percentage(self):
        """Returns food cost as a percentage of selling price."""
        return self.compute_food_cost_percentage()

    def compute_food_cost_percentage(self, total_cost=None):
        """Compute food cost %, optionally reusing a pre-computed total_cost."""
        if self.selling_price and self.selling_price > 0:
            if total_cost is None:
                total_cost = self.get_total_cost()
            return round(float(total_cost / self.selling_price) * 100, 1)
        return None

    @property
    def gross_margin_percentage(self):
        """Returns gross margin as a percentage (100 - food_cost_percentage)."""
        pct = self.food_cost_percentage
        if pct is None:
            return None
        return round(100 - pct, 1)

    @property
    def food_cost_status(self):
        """Returns 'success', 'warning', or 'danger' for Bootstrap colour coding."""
        return self.compute_food_cost_status()

    def compute_food_cost_status(self, food_cost_pct=None):
        """Compute status, optionally reusing a pre-computed percentage."""
        pct = food_cost_pct if food_cost_pct is not None else self.food_cost_percentage
        if pct is None:
            return "unknown"
        target = float(self.target_food_cost_pct or 30)
        if pct <= target:
            return "success"
        elif pct <= target + 5:
            return "warning"
        return "danger"

    class Meta:
        managed = True
        db_table = "recipes"
        indexes = [
            models.Index(fields=["type", "is_active"], name="idx_recipe_type_active"),
        ]


class RecipeComponent(models.Model):
    """DEPRECATED: Use RecipeItem instead. Keeping for migration."""

    id = models.AutoField(primary_key=True, db_column="recipe_item_id")
    parent_recipe = models.ForeignKey(
        Recipe,
        models.DO_NOTHING,
        db_column="recipe_id",
        related_name="components",
    )
    component_kind = models.CharField(max_length=50, blank=True, null=True)
    component_id = models.IntegerField(blank=True, null=True, db_column="item_id")
    quantity = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    loss_pct = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    sort_order = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "recipe_items"


class RecipeItem(models.Model):
    """
    Direct relationship between Recipe and Item (or a sub-recipe).
    Simplified model - no component_kind needed, direct item_id FK.
    """

    id = models.AutoField(primary_key=True, db_column="recipe_item_id")
    recipe = models.ForeignKey(
        Recipe,
        models.CASCADE,
        db_column="recipe_id",
        related_name="items",
    )
    # D1: item is now nullable to support sub-recipe rows
    item = models.ForeignKey(
        "Item",
        models.CASCADE,
        db_column="item_id",
        related_name="recipe_usages",
        null=True,
        blank=True,
    )
    # D1: sub-recipe ingredient support
    sub_recipe = models.ForeignKey(
        Recipe,
        models.SET_NULL,
        db_column="sub_recipe_id",
        related_name="used_in",
        null=True,
        blank=True,
        help_text="Sub-recipe used as an ingredient",
    )
    quantity = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    loss_pct = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    sort_order = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.item and not self.sub_recipe:
            raise ValidationError("Select either an inventory item or a sub-recipe.")
        if self.item and self.sub_recipe:
            raise ValidationError(
                "Cannot select both an item and a sub-recipe — choose one."
            )
        if self.sub_recipe and self.sub_recipe == self.recipe:
            raise ValidationError("A recipe cannot use itself as an ingredient.")
        if self.sub_recipe:
            self._check_circular(self.sub_recipe, visited={self.recipe_id})

    def _check_circular(self, sub, visited):
        from django.core.exceptions import ValidationError

        if sub.pk in visited:
            raise ValidationError(
                f"Circular dependency detected: {sub.name} references back to this recipe."
            )
        visited.add(sub.pk)
        for child in sub.items.filter(sub_recipe__isnull=False).select_related(
            "sub_recipe"
        ):
            self._check_circular(child.sub_recipe, visited.copy())

    def get_line_cost(self):
        """Return the cost for this ingredient line."""
        if self.sub_recipe:
            sub_cost = self.sub_recipe.get_total_cost()
            sub_yield = Decimal(str(self.sub_recipe.default_yield_qty or 1)) or Decimal(
                "1"
            )
            qty = Decimal(str(self.quantity or 0))
            loss_mult = Decimal("1") + (
                Decimal(str(self.loss_pct or 0)) / Decimal("100")
            )
            if sub_yield:
                return (sub_cost / sub_yield) * qty * loss_mult
            return Decimal("0")
        if self.item:
            from inventory.services.units_service import UnitsService

            cost_per_base = UnitsService.cost_per_base_for_item(self.item)
            qty = Decimal(str(self.quantity or 0))
            loss_pct = Decimal(str(self.loss_pct or 0))
            if qty and loss_pct and loss_pct < 100:
                try:
                    effective_qty = qty / (1 - loss_pct / 100)
                except (ArithmeticError, ZeroDivisionError):
                    effective_qty = qty
            else:
                effective_qty = qty
            return cost_per_base * effective_qty
        return Decimal("0")

    def __str__(self):
        if self.sub_recipe:
            return f"{self.recipe} - [Sub] {self.sub_recipe.name} ({self.quantity})"
        name = self.item.name if self.item else "?"
        return f"{self.recipe} - {name} ({self.quantity} {self.unit})"

    class Meta:
        managed = True
        db_table = "recipe_items_new"  # Use a new table to avoid conflicts
        # unique_together removed in D1 to support nullable item + sub_recipe rows


class SaleTransaction(models.Model):
    sale_id = models.AutoField(primary_key=True)
    recipe = models.ForeignKey(
        Recipe, models.DO_NOTHING, db_column="recipe_id", blank=True, null=True
    )
    quantity = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    user_id = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True, default="")
    sale_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale {self.pk} of {self.recipe}"

    class Meta:
        managed = True
        db_table = "sales_transactions"
