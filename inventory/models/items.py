from decimal import Decimal
from django.db import models

from . import CoerceFloatField


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, blank=False, null=False)
    parent = models.ForeignKey(
        "self",
        models.DO_NOTHING,
        db_column="parent_id",
        blank=True,
        null=True,
        related_name="children",
    )

    class Meta:
        db_table = "category"
        ordering = ("name",)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name or f"Category {self.pk}"


class Item(models.Model):
    item_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=False, null=False)
    base_unit = models.CharField(max_length=50, blank=False, null=False)
    purchase_unit = models.CharField(max_length=50, blank=False, null=False)
    category = models.ForeignKey(
        Category,
        models.DO_NOTHING,
        related_name="items",
        blank=True,
        null=True,
    )
    sub_category = models.ForeignKey(
        Category,
        models.DO_NOTHING,
        related_name="sub_items",
        blank=True,
        null=True,
    )
    permitted_departments = models.CharField(max_length=255, blank=True, null=True)
    reorder_point = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    current_stock = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=False, null=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name or f"Item {self.pk}"

    class Meta:
        db_table = "items"


class StockTransaction(models.Model):
    transaction_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(
        Item, models.DO_NOTHING, db_column="item_id", blank=True, null=True
    )
    quantity_change = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    transaction_type = models.CharField(max_length=50, blank=True, null=True)
    user_id = models.CharField(max_length=50, blank=True, null=True)
    related_mrn = models.CharField(max_length=100, blank=True, null=True)
    related_po_id = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    transaction_date = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"Transaction {self.pk} for {self.item}"

    class Meta:
        db_table = "stock_transactions"
