from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.pagination import PageNumberPagination

from ..models import (
    GoodsReceivedNote,
    GRNItem,
    Indent,
    IndentItem,
    Item,
    PurchaseOrder,
    PurchaseOrderItem,
    Recipe,
    RecipeItem,
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
    RecipeItemSerializer,
    RecipeSerializer,
    SaleTransactionSerializer,
    StockTransactionSerializer,
    SupplierSerializer,
)


class DefaultPagination(PageNumberPagination):
    """Standard pagination settings for API viewsets."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class ItemViewSet(viewsets.ModelViewSet):
    """API endpoint for CRUD operations on items.

    Query params:
        name: optional substring to filter item names.
    """

    queryset = Item.objects.all().prefetch_related("departments")
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {"name": ["exact", "icontains"]}


class SupplierViewSet(viewsets.ModelViewSet):
    """Standard CRUD API for suppliers."""

    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = "__all__"


class StockTransactionViewSet(viewsets.ModelViewSet):
    """Manage stock transactions with related item details."""

    queryset = StockTransaction.objects.all().select_related("item")
    serializer_class = StockTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = "__all__"


class IndentViewSet(viewsets.ModelViewSet):
    """CRUD API for indents with MRN and status filtering.

    Query params:
        mrn: partial match for the MRN field.
        status: exact status match.
    """

    queryset = Indent.objects.all()
    serializer_class = IndentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {"mrn": ["icontains"], "status": ["exact"]}


class IndentItemViewSet(viewsets.ModelViewSet):
    """Manage individual items within an indent."""

    queryset = IndentItem.objects.all().select_related("indent", "item")
    serializer_class = IndentItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = "__all__"


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """CRUD interface for purchase orders."""

    queryset = PurchaseOrder.objects.all().select_related("supplier")
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = "__all__"


class PurchaseOrderItemViewSet(viewsets.ModelViewSet):
    """CRUD operations for items belonging to purchase orders."""

    queryset = PurchaseOrderItem.objects.all().select_related("purchase_order", "item")
    serializer_class = PurchaseOrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = "__all__"


class GoodsReceivedNoteViewSet(viewsets.ModelViewSet):
    """API for managing goods received notes."""

    queryset = GoodsReceivedNote.objects.all().select_related(
        "purchase_order", "supplier"
    )
    serializer_class = GoodsReceivedNoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = "__all__"


class GRNItemViewSet(viewsets.ModelViewSet):
    """CRUD interface for items on a goods received note."""

    queryset = GRNItem.objects.all().select_related("grn", "po_item")
    serializer_class = GRNItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = "__all__"


class RecipeViewSet(viewsets.ModelViewSet):
    """Manage recipe records via the API."""

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = "__all__"


class RecipeItemViewSet(viewsets.ModelViewSet):
    """ViewSet for recipe items (simplified components)."""

    queryset = RecipeItem.objects.all().select_related("recipe", "item")
    serializer_class = RecipeItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = "__all__"


class SaleTransactionViewSet(viewsets.ModelViewSet):
    """Record and retrieve sale transactions."""

    queryset = SaleTransaction.objects.all().select_related("recipe")
    serializer_class = SaleTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = "__all__"
