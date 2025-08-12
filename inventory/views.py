from rest_framework import viewsets

from .models import Item, Supplier, StockTransaction, Indent, IndentItem
from .serializers import (
    ItemSerializer,
    SupplierSerializer,
    StockTransactionSerializer,
    IndentSerializer,
    IndentItemSerializer,
)


class ItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class SupplierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class StockTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockTransaction.objects.all().select_related("item")
    serializer_class = StockTransactionSerializer


class IndentViewSet(viewsets.ReadOnlyModelViewSet):
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


class IndentItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IndentItem.objects.all().select_related("indent", "item")
    serializer_class = IndentItemSerializer
