from rest_framework import serializers

from .models import (
    Indent,
    IndentItem,
    Item,
    StockTransaction,
    Supplier,
    Recipe,
    RecipeComponent,
    PurchaseOrder,
    PurchaseOrderItem,
    GoodsReceivedNote,
    GRNItem,
)


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = "__all__"


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class StockTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransaction
        fields = "__all__"


class IndentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indent
        fields = "__all__"


class IndentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndentItem
        fields = "__all__"


class PurchaseOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields = "__all__"


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = "__all__"


class GoodsReceivedNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsReceivedNote
        fields = "__all__"


class GRNItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GRNItem
        fields = "__all__"


class RecipeComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeComponent
        fields = "__all__"


class RecipeSerializer(serializers.ModelSerializer):
    components = RecipeComponentSerializer(many=True, read_only=True)

    class Meta:
        model = Recipe
        fields = "__all__"
