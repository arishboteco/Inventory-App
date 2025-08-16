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
)

router = DefaultRouter()
router.register(r"items", ItemViewSet)
router.register(r"suppliers", SupplierViewSet)
router.register(r"stock-transactions", StockTransactionViewSet)
router.register(r"indents", IndentViewSet)
router.register(r"indent-items", IndentItemViewSet)
router.register(r"recipes", RecipeViewSet)
router.register(r"recipe-components", RecipeComponentViewSet)

urlpatterns = router.urls
