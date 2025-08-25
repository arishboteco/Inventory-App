from decimal import Decimal

from django.db import models

from .fields import CoerceFloatField


class Recipe(models.Model):
    recipe_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, null=False, blank=False)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=False, null=False)
    type = models.CharField(max_length=50, blank=True, null=True)
    default_yield_qty = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    default_yield_unit = models.CharField(max_length=50, blank=True, null=True)
    plating_notes = models.TextField(blank=True, null=True)
    tags = models.JSONField(default=list, blank=True, null=True)
    version = models.IntegerField(blank=True, null=True)
    effective_from = models.DateField(auto_now_add=True)
    effective_to = models.DateField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or f"Recipe {self.pk}"

    class Meta:
        managed = False
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

    def __str__(self):
        return f"{self.parent_recipe} component #{self.pk}"

    class Meta:
        managed = False
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

    def __str__(self):
        return f"Sale {self.pk} of {self.recipe}"

    class Meta:
        managed = False
        db_table = "sales_transactions"
