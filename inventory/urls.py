from rest_framework.routers import DefaultRouter

from .views import (
    ItemViewSet,
    SupplierViewSet,
    StockTransactionViewSet,
    IndentViewSet,
    IndentItemViewSet,
)

router = DefaultRouter()
router.register(r"items", ItemViewSet)
router.register(r"suppliers", SupplierViewSet)
router.register(r"stock-transactions", StockTransactionViewSet)
router.register(r"indents", IndentViewSet)
router.register(r"indent-items", IndentItemViewSet)

urlpatterns = router.urls
