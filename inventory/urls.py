"""API routes for the inventory app."""

from rest_framework.routers import DefaultRouter

from .views import (
    ItemViewSet,
    SupplierViewSet,
    StockTransactionViewSet,
    IndentViewSet,
    IndentItemViewSet,
    RecipeViewSet,
    RecipeComponentViewSet,
    PurchaseOrderViewSet,
    PurchaseOrderItemViewSet,
    GoodsReceivedNoteViewSet,
    GRNItemViewSet,
)

router = DefaultRouter()
router.register(r"items", ItemViewSet)
router.register(r"suppliers", SupplierViewSet)
router.register(r"stock-transactions", StockTransactionViewSet)
router.register(r"indents", IndentViewSet)
router.register(r"indent-items", IndentItemViewSet)
router.register(r"recipes", RecipeViewSet)
router.register(r"recipe-components", RecipeComponentViewSet)
router.register(r"purchase-orders", PurchaseOrderViewSet)
router.register(r"purchase-order-items", PurchaseOrderItemViewSet)
router.register(r"goods-received-notes", GoodsReceivedNoteViewSet)
router.register(r"grn-items", GRNItemViewSet)

urlpatterns = router.urls
