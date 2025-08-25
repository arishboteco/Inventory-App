from rest_framework import serializers

from .models import (
    GoodsReceivedNote,
    GRNItem,
    Indent,
    IndentItem,
    Item,
    PurchaseOrder,
    PurchaseOrderItem,
    Recipe,
    RecipeComponent,
    SaleTransaction,
    StockTransaction,
    Supplier,
)


class ItemSerializer(serializers.ModelSerializer):
    """Expose basic item details and stock levels."""

    class Meta:
        model = Item
        fields = [
            "item_id",
            "name",
            "base_unit",
            "purchase_unit",
            "category_id",
            "permitted_departments",
            "reorder_point",
            "current_stock",
            "notes",
            "is_active",
            "updated_at",
        ]


class SupplierSerializer(serializers.ModelSerializer):
    """Serialize supplier contact and status information."""

    class Meta:
        model = Supplier
        fields = [
            "supplier_id",
            "name",
            "contact_person",
            "phone",
            "email",
            "address",
            "notes",
            "is_active",
            "updated_at",
        ]


class StockTransactionSerializer(serializers.ModelSerializer):
    """Show inventory adjustments for a specific item."""

    class Meta:
        model = StockTransaction
        fields = [
            "transaction_id",
            "item",
            "quantity_change",
            "transaction_type",
            "user_id",
            "user_int",
            "related_indent",
            "related_po_id",
            "notes",
            "transaction_date",
        ]


class IndentSerializer(serializers.ModelSerializer):
    """Expose requisition details submitted by departments."""

    class Meta:
        model = Indent
        fields = [
            "indent_id",
            "mrn",
            "requested_by",
            "department",
            "date_required",
            "notes",
            "status",
            "date_submitted",
            "processed_by_user_id",
            "date_processed",
            "created_at",
            "updated_at",
        ]


class IndentItemSerializer(serializers.ModelSerializer):
    """Serialize the items and quantities within an indent."""

    class Meta:
        model = IndentItem
        fields = [
            "indent_item_id",
            "indent",
            "item",
            "requested_qty",
            "issued_qty",
            "item_status",
            "notes",
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    """Provide purchase order headers sent to suppliers."""

    class Meta:
        model = PurchaseOrder
        fields = [
            "po_id",
            "supplier",
            "order_date",
            "expected_delivery_date",
            "status",
            "notes",
        ]


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """Detail quantities and prices for ordered items."""

    class Meta:
        model = PurchaseOrderItem
        fields = [
            "po_item_id",
            "purchase_order",
            "item",
            "quantity_ordered",
            "unit_price",
        ]


class GoodsReceivedNoteSerializer(serializers.ModelSerializer):
    """Serialize acknowledgments of received purchase orders."""

    class Meta:
        model = GoodsReceivedNote
        fields = [
            "grn_id",
            "purchase_order",
            "supplier",
            "received_date",
            "notes",
        ]


class GRNItemSerializer(serializers.ModelSerializer):
    """Detail items and quantities recorded on a GRN."""

    class Meta:
        model = GRNItem
        fields = [
            "grn_item_id",
            "grn",
            "po_item",
            "quantity_ordered_on_po",
            "quantity_received",
            "unit_price_at_receipt",
            "item_notes",
        ]


class SaleTransactionSerializer(serializers.ModelSerializer):
    """Expose sales of prepared recipes."""

    class Meta:
        model = SaleTransaction
        fields = [
            "sale_id",
            "recipe",
            "quantity",
            "user_id",
            "notes",
            "sale_date",
        ]


class RecipeComponentSerializer(serializers.ModelSerializer):
    """Serialize components that make up a recipe."""

    class Meta:
        model = RecipeComponent
        fields = [
            "id",
            "parent_recipe",
            "component_kind",
            "component_id",
            "quantity",
            "unit",
            "loss_pct",
            "sort_order",
            "notes",
            "created_at",
            "updated_at",
        ]


class RecipeSerializer(serializers.ModelSerializer):
    """Represent a recipe and its component breakdown."""

    components = RecipeComponentSerializer(many=True, read_only=True)

    class Meta:
        model = Recipe
        fields = [
            "recipe_id",
            "name",
            "description",
            "is_active",
            "type",
            "default_yield_qty",
            "default_yield_unit",
            "plating_notes",
            "tags",
            "version",
            "effective_from",
            "effective_to",
            "created_at",
            "updated_at",
            "components",
        ]
