"""API routes for the inventory app."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    GoodsReceivedNoteViewSet,
    GRNItemViewSet,
    IndentItemViewSet,
    IndentViewSet,
    ItemViewSet,
    PurchaseOrderItemViewSet,
    PurchaseOrderViewSet,
    RecipeComponentViewSet,
    RecipeViewSet,
    SaleTransactionViewSet,
    StockTransactionViewSet,
    SupplierViewSet,
)
from .views.items import ItemsExportView

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
router.register(r"sale-transactions", SaleTransactionViewSet)

urlpatterns = router.urls + [
    path("items/export/", ItemsExportView.as_view(), name="items_export_api"),
]
