from decimal import Decimal

from django.db import models
from django.db.models import Sum

from .items import Item
from .suppliers import Supplier


class Indent(models.Model):
    """Represents a material requisition from a department."""

    indent_id = models.AutoField(primary_key=True)
    mrn = models.CharField(max_length=100, unique=True, null=False, blank=False)
    requested_by = models.CharField(max_length=255, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    date_required = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    date_submitted = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    processed_by_user_id = models.CharField(max_length=50, blank=True, null=True)
    date_processed = models.DateTimeField(auto_now=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.mrn or f"Indent {self.pk}"

    class Meta:
        managed = False
        db_table = "indents"


class IndentItem(models.Model):
    """Links an item to an indent with requested and issued quantities."""

    indent_item_id = models.AutoField(primary_key=True)
    indent = models.ForeignKey(
        Indent, models.DO_NOTHING, db_column="indent_id", blank=True, null=True
    )
    item = models.ForeignKey(
        Item, models.DO_NOTHING, db_column="item_id", blank=True, null=True
    )
    requested_qty = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    issued_qty = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    item_status = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.indent} - {self.item}"

    class Meta:
        managed = False
        db_table = "indent_items"


class PurchaseOrder(models.Model):
    """Orders items from a supplier based on approved indents."""

    po_id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey(Supplier, models.CASCADE, db_column="supplier_id")
    order_date = models.DateField()
    expected_delivery_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("DRAFT", "Draft"),
            ("ORDERED", "Ordered"),
            ("PARTIAL", "Partially Received"),
            ("COMPLETE", "Completed"),
            ("CANCELLED", "Cancelled"),
        ],
        default="DRAFT",
    )
    notes = models.TextField(blank=True, null=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"PO {self.pk} to {self.supplier}"

    class Meta:
        managed = False
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

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.purchase_order} - {self.item}"

    class Meta:
        managed = False
        db_table = "purchase_order_items"


class GoodsReceivedNote(models.Model):
    """Acknowledges receipt of goods for a purchase order."""

    grn_id = models.AutoField(primary_key=True)
    purchase_order = models.ForeignKey(PurchaseOrder, models.CASCADE, db_column="po_id")
    supplier = models.ForeignKey(Supplier, models.CASCADE, db_column="supplier_id")
    received_date = models.DateField()
    notes = models.TextField(blank=True, null=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"GRN {self.pk} for PO {self.purchase_order_id}"

    class Meta:
        managed = False
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
    item_notes = models.TextField(blank=True, null=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.grn} item {self.po_item}"

    class Meta:
        managed = False
        db_table = "grn_items"
