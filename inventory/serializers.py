from rest_framework import serializers

from .models import Item, Supplier, StockTransaction, Indent, IndentItem


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
