# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Items(models.Model):
    item_id = models.AutoField(primary_key=True, blank=True, null=True)
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
        db_table = 'items'


class Suppliers(models.Model):
    supplier_id = models.AutoField(primary_key=True, blank=True, null=True)
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
        db_table = 'suppliers'


class StockTransactions(models.Model):
    transaction_id = models.AutoField(primary_key=True, blank=True, null=True)
    item = models.ForeignKey(Items, models.DO_NOTHING, blank=True, null=True)
    quantity_change = models.FloatField(blank=True, null=True)
    transaction_type = models.TextField(blank=True, null=True)
    user_id = models.TextField(blank=True, null=True)
    related_mrn = models.TextField(blank=True, null=True)
    related_po_id = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    transaction_date = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stock_transactions'


class Indents(models.Model):
    indent_id = models.AutoField(primary_key=True, blank=True, null=True)
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
        db_table = 'indents'


class IndentItems(models.Model):
    indent_item_id = models.AutoField(primary_key=True, blank=True, null=True)
    indent = models.ForeignKey(Indents, models.DO_NOTHING, blank=True, null=True)
    item = models.ForeignKey(Items, models.DO_NOTHING, blank=True, null=True)
    requested_qty = models.FloatField(blank=True, null=True)
    issued_qty = models.FloatField(blank=True, null=True)
    item_status = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'indent_items'
