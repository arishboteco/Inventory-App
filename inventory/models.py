from decimal import Decimal, InvalidOperation
from django.db import models
from django.db.models import Sum


class CoerceFloatField(models.DecimalField):
    """DecimalField that coerces invalid values to Decimal('0')."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 10)
        kwargs.setdefault("decimal_places", 2)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return Decimal("0")
        try:
            return Decimal(value)
        except (TypeError, ValueError, InvalidOperation):
            return Decimal("0")

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)


class Item(models.Model):
    item_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    base_unit = models.CharField(max_length=50, blank=True, null=True)
    purchase_unit = models.CharField(max_length=50, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    sub_category = models.CharField(max_length=100, blank=True, null=True)
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


class Supplier(models.Model):
    supplier_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, null=False, blank=False)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=False, null=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name or f"Supplier {self.pk}"

    class Meta:
        db_table = "suppliers"


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


class Recipe(models.Model):
    recipe_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, null=False, blank=False)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=False, null=False)
    type = models.CharField(max_length=50, blank=True, null=True)
    default_yield_qty = CoerceFloatField(default=Decimal("0"), blank=True, null=True)
    default_yield_unit = models.CharField(max_length=50, blank=True, null=True)
    plating_notes = models.TextField(blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True, null=True)
    version = models.IntegerField(blank=True, null=True)
    effective_from = models.DateField(auto_now_add=True)
    effective_to = models.DateField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name or f"Recipe {self.pk}"

    class Meta:
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

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.parent_recipe} component #{self.pk}"

    class Meta:
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

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"Sale {self.pk} of {self.recipe}"

    class Meta:
        db_table = "sales_transactions"


class Indent(models.Model):
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
        db_table = "indents"


class IndentItem(models.Model):
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

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"PO {self.pk} to {self.supplier}"

    class Meta:
        db_table = "purchase_orders"


class PurchaseOrderItem(models.Model):
    po_item_id = models.AutoField(primary_key=True)
    purchase_order = models.ForeignKey(
        PurchaseOrder, models.CASCADE, db_column="po_id"
    )
    item = models.ForeignKey(Item, models.DO_NOTHING, db_column="item_id")
    quantity_ordered = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def received_total(self) -> Decimal:
        value = self.__dict__.get("_received_total")
        if value is not None:
            return value or Decimal("0")
        total = (
            self.grnitem_set.aggregate(total=Sum("quantity_received"))["total"]
            or Decimal("0")
        )
        return total

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.purchase_order} - {self.item}"

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

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"GRN {self.pk} for PO {self.purchase_order_id}"

    class Meta:
        db_table = "goods_received_notes"


class GRNItem(models.Model):
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
        db_table = "grn_items"
