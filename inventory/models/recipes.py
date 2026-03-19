from decimal import Decimal

from django.db import models

from .fields import CoerceFloatField

RECIPE_TYPES = [
    ("", "Select type..."),
    ("MAIN", "Main Course"),
    ("APPETIZER", "Appetizer / Starter"),
    ("DESSERT", "Dessert"),
    ("BEVERAGE", "Beverage"),
    ("PREP", "Prep / Base Recipe"),
    ("SAUCE", "Sauce / Dressing"),
    ("SIDE", "Side Dish"),
    ("BATCH", "Batch Production"),
    ("OTHER", "Other"),
]


class Recipe(models.Model):
    recipe_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, null=False, blank=False)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=False, null=False)
    type = models.CharField(max_length=50, blank=True, null=True, choices=RECIPE_TYPES)
    default_yield_qty = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    default_yield_unit = models.CharField(max_length=50, blank=True, null=True)
    plating_notes = models.TextField(blank=True, null=True, default="")
    tags = models.JSONField(default=list, blank=True, null=True)
    version = models.IntegerField(blank=True, null=True)
    effective_from = models.DateField(auto_now_add=True)
    effective_to = models.DateField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or f"Recipe {self.pk}"

    class Meta:
        managed = True
        db_table = "recipes"


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
    Direct relationship between Recipe and Item.
    Simplified model - no component_kind needed, direct item_id FK.
    """

    id = models.AutoField(primary_key=True, db_column="recipe_item_id")
    recipe = models.ForeignKey(
        Recipe,
        models.CASCADE,
        db_column="recipe_id",
        related_name="items",
    )
    item = models.ForeignKey(
        "Item",
        models.CASCADE,
        db_column="item_id",
        related_name="recipe_usages",
    )
    quantity = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    loss_pct = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    sort_order = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.recipe} - {self.item.name} ({self.quantity} {self.unit})"

    class Meta:
        managed = True
        db_table = "recipe_items_new"  # Use a new table to avoid conflicts
        unique_together = ("recipe", "item")


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
