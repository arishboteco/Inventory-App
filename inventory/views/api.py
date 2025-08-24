from rest_framework import permissions, viewsets

from ..models import (
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
from ..serializers import (
    GoodsReceivedNoteSerializer,
    GRNItemSerializer,
    IndentItemSerializer,
    IndentSerializer,
    ItemSerializer,
    PurchaseOrderItemSerializer,
    PurchaseOrderSerializer,
    RecipeComponentSerializer,
    RecipeSerializer,
    SaleTransactionSerializer,
    StockTransactionSerializer,
    SupplierSerializer,
)


class ItemViewSet(viewsets.ModelViewSet):
    """API endpoint for CRUD operations on items.

    Query params:
        name: optional substring to filter item names.
    """

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
    """Standard CRUD API for suppliers."""

    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]


class StockTransactionViewSet(viewsets.ModelViewSet):
    """Manage stock transactions with related item details."""

    queryset = StockTransaction.objects.all().select_related("item")
    serializer_class = StockTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]


class IndentViewSet(viewsets.ModelViewSet):
    """CRUD API for indents with MRN and status filtering.

    Query params:
        mrn: partial match for the MRN field.
        status: exact status match.
    """

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
    """Manage individual items within an indent."""

    queryset = IndentItem.objects.all().select_related("indent", "item")
    serializer_class = IndentItemSerializer
    permission_classes = [permissions.IsAuthenticated]


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """CRUD interface for purchase orders."""

    queryset = PurchaseOrder.objects.all().select_related("supplier")
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated]


class PurchaseOrderItemViewSet(viewsets.ModelViewSet):
    """CRUD operations for items belonging to purchase orders."""

    queryset = PurchaseOrderItem.objects.all().select_related("purchase_order", "item")
    serializer_class = PurchaseOrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]


class GoodsReceivedNoteViewSet(viewsets.ModelViewSet):
    """API for managing goods received notes."""

    queryset = GoodsReceivedNote.objects.all().select_related(
        "purchase_order", "supplier"
    )
    serializer_class = GoodsReceivedNoteSerializer
    permission_classes = [permissions.IsAuthenticated]


class GRNItemViewSet(viewsets.ModelViewSet):
    """CRUD interface for items on a goods received note."""

    queryset = GRNItem.objects.all().select_related("grn", "po_item")
    serializer_class = GRNItemSerializer
    permission_classes = [permissions.IsAuthenticated]


class RecipeViewSet(viewsets.ModelViewSet):
    """Manage recipe records via the API."""

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticated]


class RecipeComponentViewSet(viewsets.ModelViewSet):
    """CRUD API for components that make up a recipe."""

    queryset = RecipeComponent.objects.all().select_related("parent_recipe")
    serializer_class = RecipeComponentSerializer
    permission_classes = [permissions.IsAuthenticated]


class SaleTransactionViewSet(viewsets.ModelViewSet):
    """Record and retrieve sale transactions."""

    queryset = SaleTransaction.objects.all().select_related("recipe")
    serializer_class = SaleTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
