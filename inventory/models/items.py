from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .fields import CoerceFloatField
from .units import Unit


class Item(models.Model):
    """An inventory item and its stock tracking details."""

    item_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    unit = models.ForeignKey(
        Unit,
        models.PROTECT,
        db_column="unit_id",
        related_name="items",
    )
    category_id = models.BigIntegerField(
        blank=True, null=True, db_column="category_id_ref"
    )

    # Business fields for complete item management
    base_unit = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Base unit of measurement (kg, ltr, pc)",
    )
    purchase_unit = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Purchase unit (g, ml, each)",
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Item category",
    )
    sub_category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Item subcategory",
    )

    # Purchase and supplier information
    initial_purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        help_text="Initial purchase price per unit"
    )
    last_purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        help_text="Most recent purchase price per unit"
    )
    preferred_supplier = models.ForeignKey(
        'Supplier', on_delete=models.SET_NULL, blank=True, null=True,
        related_name='preferred_items', help_text="Default supplier for this item"
    )
    minimum_order_qty = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        help_text="Minimum order quantity"
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
        help_text="Additional notes about this item",
    )
    is_active = models.BooleanField(default=True, null=False)
    updated_at = models.DateTimeField(auto_now=True)

    # Many-to-many relationship with departments
    departments = models.ManyToManyField(
        'Department',
        through='ItemDepartment',
        related_name='items',
        blank=True
    )

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name or f"Item {self.pk}"

    @property
    def department_names(self):
        """Return a comma-separated string of department names."""
        return ", ".join(self.departments.values_list('name', flat=True))

    class Meta:
        managed = True
        db_table = "items"

    def clean(self):
        if self.unit_id and not Unit.objects.filter(pk=self.unit_id).exists():
            raise ValidationError({"unit": "Selected unit does not exist in units table."})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


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
    notes = models.TextField(blank=True, null=True)
    transaction_date = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"Transaction {self.pk} for {self.item}"

    class Meta:
        managed = True
        db_table = "stock_transactions"
