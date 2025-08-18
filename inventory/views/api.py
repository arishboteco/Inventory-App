from rest_framework import viewsets

from ..models import (
    Item,
    Supplier,
    StockTransaction,
    Indent,
    IndentItem,
    Recipe,
    RecipeComponent,
    PurchaseOrder,
    PurchaseOrderItem,
    GoodsReceivedNote,
    GRNItem,
)
from ..serializers import (
    ItemSerializer,
    SupplierSerializer,
    StockTransactionSerializer,
    IndentSerializer,
    IndentItemSerializer,
    RecipeSerializer,
    RecipeComponentSerializer,
    PurchaseOrderSerializer,
    PurchaseOrderItemSerializer,
    GoodsReceivedNoteSerializer,
    GRNItemSerializer,
)


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class StockTransactionViewSet(viewsets.ModelViewSet):
    queryset = StockTransaction.objects.all().select_related("item")
    serializer_class = StockTransactionSerializer


class IndentViewSet(viewsets.ModelViewSet):
    queryset = Indent.objects.all()
    serializer_class = IndentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        mrn = self.request.query_params.get("mrn")
        status = self.request.query_params.get("status")
        if mrn:
            queryset = queryset.filter(mrn__icontains=mrn)
        if status:
            queryset = queryset.filter(status=status)
        return queryset


class IndentItemViewSet(viewsets.ModelViewSet):
    queryset = IndentItem.objects.all().select_related("indent", "item")
    serializer_class = IndentItemSerializer


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all().select_related("supplier")
    serializer_class = PurchaseOrderSerializer


class PurchaseOrderItemViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrderItem.objects.all().select_related("purchase_order", "item")
    serializer_class = PurchaseOrderItemSerializer


class GoodsReceivedNoteViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceivedNote.objects.all().select_related("purchase_order", "supplier")
    serializer_class = GoodsReceivedNoteSerializer


class GRNItemViewSet(viewsets.ModelViewSet):
    queryset = GRNItem.objects.all().select_related("grn", "po_item")
    serializer_class = GRNItemSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer


class RecipeComponentViewSet(viewsets.ModelViewSet):
    queryset = RecipeComponent.objects.all().select_related("parent_recipe")
    serializer_class = RecipeComponentSerializer
