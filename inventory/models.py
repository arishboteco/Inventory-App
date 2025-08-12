from django.db import models


class Item(models.Model):
    item_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    base_unit = models.CharField(max_length=50, blank=True, null=True)
    purchase_unit = models.CharField(max_length=50, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    sub_category = models.CharField(max_length=100, blank=True, null=True)
    permitted_departments = models.TextField(blank=True, null=True)
    reorder_point = models.FloatField(blank=True, null=True)
    current_stock = models.FloatField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "items"
        managed = False


class Supplier(models.Model):
    supplier_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "suppliers"
        managed = False


class StockTransaction(models.Model):
    transaction_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(Item, on_delete=models.DO_NOTHING)
    quantity_change = models.FloatField()
    transaction_type = models.CharField(max_length=50)
    user_id = models.CharField(max_length=255, blank=True, null=True)
    related_mrn = models.CharField(max_length=50, blank=True, null=True)
    related_po_id = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    transaction_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "stock_transactions"
        managed = False


class Indent(models.Model):
    indent_id = models.AutoField(primary_key=True)
    mrn = models.CharField(max_length=50, unique=True)
    requested_by = models.CharField(max_length=255)
    department = models.CharField(max_length=100)
    date_required = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50)
    date_submitted = models.DateTimeField(blank=True, null=True)
    processed_by_user_id = models.CharField(max_length=255, blank=True, null=True)
    date_processed = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "indents"
        managed = False


class IndentItem(models.Model):
    indent_item_id = models.AutoField(primary_key=True)
    indent = models.ForeignKey(Indent, on_delete=models.DO_NOTHING)
    item = models.ForeignKey(Item, on_delete=models.DO_NOTHING)
    requested_qty = models.FloatField()
    issued_qty = models.FloatField(blank=True, null=True)
    item_status = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "indent_items"
        managed = False
