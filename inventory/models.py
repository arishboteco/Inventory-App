from django.db import models


class Item(models.Model):
    item_id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    base_unit = models.TextField(blank=True, null=True)
    purchase_unit = models.TextField(blank=True, null=True)
    category = models.TextField(blank=True, null=True)
    sub_category = models.TextField(blank=True, null=True)
    permitted_departments = models.TextField(blank=True, null=True)
    reorder_point = models.FloatField(blank=True, null=True)
    current_stock = models.FloatField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    updated_at = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "items"


class Supplier(models.Model):
    supplier_id = models.AutoField(primary_key=True)
    name = models.TextField(unique=True, blank=True, null=True)
    contact_person = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    updated_at = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "suppliers"


class StockTransaction(models.Model):
    transaction_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(
        Item, models.DO_NOTHING, db_column="item_id", blank=True, null=True
    )
    quantity_change = models.FloatField(blank=True, null=True)
    transaction_type = models.TextField(blank=True, null=True)
    user_id = models.TextField(blank=True, null=True)
    related_mrn = models.TextField(blank=True, null=True)
    related_po_id = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    transaction_date = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "stock_transactions"


class Indent(models.Model):
    indent_id = models.AutoField(primary_key=True)
    mrn = models.TextField(unique=True, blank=True, null=True)
    requested_by = models.TextField(blank=True, null=True)
    department = models.TextField(blank=True, null=True)
    date_required = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)
    date_submitted = models.TextField(blank=True, null=True)
    processed_by_user_id = models.TextField(blank=True, null=True)
    date_processed = models.TextField(blank=True, null=True)
    created_at = models.TextField(blank=True, null=True)
    updated_at = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "indents"


class IndentItem(models.Model):
    indent_item_id = models.AutoField(primary_key=True)
    indent = models.ForeignKey(
        Indent, models.DO_NOTHING, db_column="indent_id", blank=True, null=True
    )
    item = models.ForeignKey(
        Item, models.DO_NOTHING, db_column="item_id", blank=True, null=True
    )
    requested_qty = models.FloatField(blank=True, null=True)
    issued_qty = models.FloatField(blank=True, null=True)
    item_status = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "indent_items"


class PurchaseOrder(models.Model):
    po_id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey(
        Supplier, models.CASCADE, db_column="supplier_id"
    )
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

    class Meta:
        db_table = "purchase_orders"


class PurchaseOrderItem(models.Model):
    po_item_id = models.AutoField(primary_key=True)
    purchase_order = models.ForeignKey(
        PurchaseOrder, models.CASCADE, db_column="po_id"
    )
    item = models.ForeignKey(Item, models.DO_NOTHING, db_column="item_id")
    quantity_ordered = models.FloatField()
    quantity_received = models.FloatField(default=0)
    unit_price = models.FloatField()

    class Meta:
        db_table = "purchase_order_items"


class GoodsReceivedNote(models.Model):
    grn_id = models.AutoField(primary_key=True)
    purchase_order = models.ForeignKey(
        PurchaseOrder, models.CASCADE, db_column="po_id"
    )
    supplier = models.ForeignKey(
        Supplier, models.CASCADE, db_column="supplier_id"
    )
    received_date = models.DateField()
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "goods_received_notes"


class GRNItem(models.Model):
    grn_item_id = models.AutoField(primary_key=True)
    grn = models.ForeignKey(GoodsReceivedNote, models.CASCADE, db_column="grn_id")
    po_item = models.ForeignKey(
        PurchaseOrderItem, models.CASCADE, db_column="po_item_id"
    )
    quantity_ordered_on_po = models.FloatField()
    quantity_received = models.FloatField()
    unit_price_at_receipt = models.FloatField()
    item_notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "grn_items"
