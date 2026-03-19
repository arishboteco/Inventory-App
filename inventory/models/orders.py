from decimal import Decimal

from django.db import models
from django.db.models import Sum

from .departments import Department
from .enums import IndentStatus, ItemStatus, PurchaseOrderStatus
from .items import Item
from .suppliers import Supplier


class Indent(models.Model):
    """Represents a material requisition from a department."""

    indent_id = models.AutoField(primary_key=True)
    mrn = models.CharField(max_length=100, unique=True, null=False, blank=False)
    requested_by = models.CharField(max_length=255, blank=True, null=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        db_column="department_id",
        blank=True,
        null=True,
    )
    date_required = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True, default="")
    status = models.CharField(
        max_length=50,
        choices=IndentStatus.choices,
        default=IndentStatus.SUBMITTED,
        blank=True,
        null=True,
    )
    date_submitted = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    processed_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        db_column="processed_by_id",
    )
    date_processed = models.DateTimeField(auto_now=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.mrn or f"Indent {self.pk}"

    class Meta:
        managed = True
        db_table = "indents"


class IndentItem(models.Model):
    """Links an item to an indent with requested and issued quantities."""

    indent_item_id = models.AutoField(primary_key=True)
    indent = models.ForeignKey(
        Indent, models.PROTECT, db_column="indent_id", blank=True, null=True
    )
    item = models.ForeignKey(
        Item, models.PROTECT, db_column="item_id", blank=True, null=True
    )
    requested_qty = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    issued_qty = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    item_status = models.CharField(
        max_length=50,
        choices=ItemStatus.choices,
        default=ItemStatus.PENDING,
        blank=True,
        null=True,
    )
    notes = models.TextField(blank=True, null=True, default="")

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.indent} - {self.item}"

    class Meta:
        managed = True
        db_table = "indent_items"


class PurchaseOrder(models.Model):
    """Orders items from a supplier based on approved indents."""

    po_id = models.AutoField(primary_key=True)
    po_number = models.TextField(default="")
    supplier = models.ForeignKey(Supplier, models.CASCADE, db_column="supplier_id")
    order_date = models.DateField()
    expected_delivery_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=PurchaseOrderStatus.choices,
        default=PurchaseOrderStatus.DRAFT,
    )
    notes = models.TextField(blank=True, null=True, default="")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.po_number:
            self.po_number = f"PO-{self.po_id:04d}"
            super().save(update_fields=["po_number"])

    def __str__(self) -> str:  # pragma: no cover - simple representation
        label = self.po_number or f"PO {self.pk}"
        return f"{label} to {self.supplier}"

    class Meta:
        managed = True
        db_table = "purchase_orders"


class PurchaseOrderItem(models.Model):
    """Line item detailing quantity and price for a purchase order."""

    po_item_id = models.AutoField(primary_key=True)
    purchase_order = models.ForeignKey(PurchaseOrder, models.CASCADE, db_column="po_id")
    item = models.ForeignKey(Item, models.DO_NOTHING, db_column="item_id")
    quantity_ordered = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def received_total(self) -> Decimal:
        value = self.__dict__.get("_received_total")
        if value is not None:
            return value or Decimal("0")
        total = self.grnitem_set.aggregate(total=Sum("quantity_received"))[
            "total"
        ] or Decimal("0")
        return total

    @property
    def line_total(self) -> Decimal:
        """Calculate line total (quantity × unit price)."""
        return self.quantity_ordered * self.unit_price

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.purchase_order} - {self.item}"

    def save(self, *args, **kwargs):
        """Override save to update item purchase price history."""
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Update item's last purchase price when PO item is created/updated
        if self.item and self.unit_price:
            # Only update if this is a new record or price changed
            update_price = False
            if is_new:
                update_price = True
            else:
                # Check if price changed
                old_item = PurchaseOrderItem.objects.get(pk=self.pk)
                if old_item.unit_price != self.unit_price:
                    update_price = True

            if update_price:
                # Update item's price history
                Item.objects.filter(pk=self.item.pk).update(
                    last_purchase_price=self.unit_price
                )

    class Meta:
        managed = True
        db_table = "purchase_order_items"


class IndentPOLink(models.Model):
    """Links an indent line to its planned purchase order line."""

    link_id = models.AutoField(primary_key=True)
    indent_item = models.ForeignKey(
        "inventory.IndentItem",
        models.CASCADE,
        db_column="indent_item_id",
        related_name="po_links",
    )
    po_item = models.ForeignKey(
        PurchaseOrderItem,
        models.CASCADE,
        db_column="po_item_id",
        related_name="indent_links",
    )
    planned_qty = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = True
        db_table = "indent_po_links"


class GoodsReceivedNote(models.Model):
    """Acknowledges receipt of goods for a purchase order."""

    grn_id = models.AutoField(primary_key=True)
    purchase_order = models.ForeignKey(PurchaseOrder, models.CASCADE, db_column="po_id")
    supplier = models.ForeignKey(Supplier, models.CASCADE, db_column="supplier_id")
    received_date = models.DateField()
    notes = models.TextField(blank=True, null=True, default="")
    attachment = models.FileField(upload_to="grn_attachments/", blank=True, null=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"GRN {self.pk} for PO {self.purchase_order_id}"

    class Meta:
        managed = True
        db_table = "goods_received_notes"


class GRNItem(models.Model):
    """Tracks individual items received against a GRN and PO item."""

    grn_item_id = models.AutoField(primary_key=True)
    grn = models.ForeignKey(GoodsReceivedNote, models.CASCADE, db_column="grn_id")
    po_item = models.ForeignKey(
        PurchaseOrderItem, models.CASCADE, db_column="po_item_id"
    )
    quantity_ordered_on_po = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price_at_receipt = models.DecimalField(max_digits=10, decimal_places=2)
    item_notes = models.TextField(blank=True, null=True, default="", db_column="notes")

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.grn} item {self.po_item}"

    class Meta:
        managed = True
        db_table = "grn_items"
