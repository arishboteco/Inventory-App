from rest_framework import permissions, viewsets

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
    SaleTransaction,
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
    SaleTransactionSerializer,
)


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]


class StockTransactionViewSet(viewsets.ModelViewSet):
    queryset = StockTransaction.objects.all().select_related("item")
    serializer_class = StockTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]


class IndentViewSet(viewsets.ModelViewSet):
    queryset = Indent.objects.all()
    serializer_class = IndentSerializer
    permission_classes = [permissions.IsAuthenticated]

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
    permission_classes = [permissions.IsAuthenticated]


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all().select_related("supplier")
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated]


class PurchaseOrderItemViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrderItem.objects.all().select_related("purchase_order", "item")
    serializer_class = PurchaseOrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]


class GoodsReceivedNoteViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceivedNote.objects.all().select_related("purchase_order", "supplier")
    serializer_class = GoodsReceivedNoteSerializer
    permission_classes = [permissions.IsAuthenticated]


class GRNItemViewSet(viewsets.ModelViewSet):
    queryset = GRNItem.objects.all().select_related("grn", "po_item")
    serializer_class = GRNItemSerializer
    permission_classes = [permissions.IsAuthenticated]


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticated]


class RecipeComponentViewSet(viewsets.ModelViewSet):
    queryset = RecipeComponent.objects.all().select_related("parent_recipe")
    serializer_class = RecipeComponentSerializer
    permission_classes = [permissions.IsAuthenticated]


class SaleTransactionViewSet(viewsets.ModelViewSet):
    queryset = SaleTransaction.objects.all().select_related("recipe")
    serializer_class = SaleTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
