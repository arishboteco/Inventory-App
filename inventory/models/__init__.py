from decimal import Decimal, InvalidOperation
from django.db import models


class CoerceFloatField(models.DecimalField):
    """DecimalField that coerces invalid values to Decimal('0')."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 10)
        kwargs.setdefault("decimal_places", 2)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return Decimal("0")
        try:
            return Decimal(value)
        except (TypeError, ValueError, InvalidOperation):
            return Decimal("0")

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)


from .items import Category, Item, StockTransaction
from .suppliers import Supplier
from .orders import (
    Indent,
    IndentItem,
    PurchaseOrder,
    PurchaseOrderItem,
    GoodsReceivedNote,
    GRNItem,
)


class Recipe(models.Model):
    recipe_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, null=False, blank=False)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=False, null=False)
    type = models.CharField(max_length=50, blank=True, null=True)
    default_yield_qty = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    default_yield_unit = models.CharField(max_length=50, blank=True, null=True)
    plating_notes = models.TextField(blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True, null=True)
    version = models.IntegerField(blank=True, null=True)
    effective_from = models.DateField(auto_now_add=True)
    effective_to = models.DateField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name or f"Recipe {self.pk}"

    class Meta:
        db_table = "recipes"


class RecipeComponent(models.Model):
    id = models.AutoField(primary_key=True)
    parent_recipe = models.ForeignKey(
        Recipe,
        models.DO_NOTHING,
        db_column="parent_recipe_id",
        related_name="components",
    )
    component_kind = models.CharField(max_length=50, blank=True, null=True)
    component_id = models.IntegerField(blank=True, null=True)
    quantity = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    loss_pct = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    sort_order = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.parent_recipe} component #{self.pk}"

    class Meta:
        db_table = "recipe_components"
        unique_together = ("parent_recipe", "component_kind", "component_id")


class SaleTransaction(models.Model):
    sale_id = models.AutoField(primary_key=True)
    recipe = models.ForeignKey(
        Recipe, models.DO_NOTHING, db_column="recipe_id", blank=True, null=True
    )
    quantity = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    user_id = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    sale_date = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"Sale {self.pk} of {self.recipe}"

    class Meta:
        db_table = "sales_transactions"


__all__ = [
    "CoerceFloatField",
    "Category",
    "Item",
    "StockTransaction",
    "Supplier",
    "Indent",
    "IndentItem",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "GoodsReceivedNote",
    "GRNItem",
    "Recipe",
    "RecipeComponent",
    "SaleTransaction",
]
