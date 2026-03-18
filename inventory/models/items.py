from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property

from .category import Category
from .fields import CoerceFloatField
from .unit import Unit


class Item(models.Model):
    """An inventory item and its stock tracking details."""

    item_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        db_column="unit_id",
        blank=False,
        null=False,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        db_column="category_id_ref",
        blank=True,
        null=True,
    )

    # Purchase and supplier information
    initial_purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Initial purchase price per unit",
    )
    last_purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Most recent purchase price per unit",
    )
    preferred_supplier = models.ForeignKey(
        "Supplier",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="preferred_items",
        help_text="Default supplier for this item",
    )
    minimum_order_qty = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum order quantity",
    )
    lead_time_days = models.IntegerField(
        blank=True, null=True, help_text="Standard lead time in days"
    )

    # Original fields
    reorder_point = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    current_stock = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    notes = models.TextField(
        blank=True,
        null=True,
        default="",
        help_text="Additional notes about this item",
    )
    is_active = models.BooleanField(default=True, null=False)
    updated_at = models.DateTimeField(auto_now=True)

    # Many-to-many relationship with departments
    departments = models.ManyToManyField(
        "Department", through="ItemDepartment", related_name="items", blank=True
    )

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name or f"Item {self.pk}"

    @cached_property
    def department_names(self):
        """Return a comma-separated string of department names.

        Cached per instance to avoid recomputing the joined list when accessed
        multiple times. Prefetching ``departments`` ensures this does not hit
        the database repeatedly.
        """
        return ", ".join(dept.name for dept in self.departments.all())

    class Meta:
        managed = True
        db_table = "items"
        indexes = [
            models.Index(fields=["name"], name="item_name_idx"),
            models.Index(fields=["current_stock"], name="item_cstock_idx"),
            models.Index(fields=["reorder_point"], name="item_rop_idx"),
            models.Index(fields=["is_active"], name="item_active_idx"),
        ]


class StockTransaction(models.Model):
    """Records inventory stock increases or decreases for an item."""

    transaction_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(
        Item, models.PROTECT, db_column="item_id", blank=True, null=True
    )
    quantity_change = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    transaction_type = models.CharField(max_length=50, blank=True, null=True)
    user_id = models.CharField(max_length=50, blank=True, null=True)
    user_int = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.SET_NULL,
        db_column="user_id_int",
        blank=True,
        null=True,
    )
    related_indent = models.ForeignKey(
        "inventory.Indent",
        models.SET_NULL,
        db_column="related_indent_id",
        blank=True,
        null=True,
    )
    related_po = models.ForeignKey(
        "inventory.PurchaseOrder",
        models.SET_NULL,
        db_column="related_po_id",
        blank=True,
        null=True,
    )
    notes = models.TextField(blank=True, null=True, default="")
    reason_category = models.CharField(max_length=20, blank=True, null=True)
    transaction_date = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"Transaction {self.pk} for {self.item}"

    class Meta:
        managed = True
        db_table = "stock_transactions"
        indexes = [
            models.Index(fields=["transaction_date"], name="stx_date_idx"),
            models.Index(fields=["transaction_type"], name="stx_type_idx"),
            models.Index(fields=["item", "transaction_date"], name="stx_item_date_idx"),
        ]


class StockSnapshot(models.Model):
    """Daily stock level snapshot for trend analysis and forecasting."""

    item = models.ForeignKey(
        Item, on_delete=models.CASCADE, related_name="snapshots"
    )
    snapshot_date = models.DateField(db_index=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    value = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    class Meta:
        managed = True
        db_table = "stock_snapshots"
        unique_together = ("item", "snapshot_date")
        ordering = ["snapshot_date"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Snapshot {self.snapshot_date} — {self.item}"
