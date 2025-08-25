from decimal import Decimal

from django.conf import settings
from django.db import models

from .fields import CoerceFloatField


class Item(models.Model):
    """An inventory item and its stock tracking details."""

    item_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    base_unit = models.CharField(max_length=50, blank=False, null=False)
    purchase_unit = models.CharField(max_length=50, blank=False, null=False)
    category_id = models.BigIntegerField(
        blank=True, null=True, db_column="category_id_ref"
    )
    permitted_departments = models.CharField(max_length=255, blank=True, null=True)
    reorder_point = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    current_stock = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, null=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name or f"Item {self.pk}"

    class Meta:
        managed = False
        db_table = "items"


class StockTransaction(models.Model):
    """Records inventory stock increases or decreases for an item."""

    transaction_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(
        Item, models.DO_NOTHING, db_column="item_id", blank=True, null=True
    )
    quantity_change = CoerceFloatField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    transaction_type = models.CharField(max_length=50, blank=True, null=True)
    user_id = models.CharField(max_length=50, blank=True, null=True)
    user_int = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.DO_NOTHING,
        db_column="user_id_int",
        blank=True,
        null=True,
    )
    related_indent = models.ForeignKey(
        "inventory.Indent",
        models.DO_NOTHING,
        db_column="related_indent_id",
        blank=True,
        null=True,
    )
    related_po_id = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    transaction_date = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"Transaction {self.pk} for {self.item}"

    class Meta:
        managed = False
        db_table = "stock_transactions"
