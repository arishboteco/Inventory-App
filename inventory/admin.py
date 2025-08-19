from django.contrib import admin

from .models import (
    GRNItem,
    GoodsReceivedNote,
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


for model in [
    Item,
    Supplier,
    StockTransaction,
    Recipe,
    RecipeComponent,
    SaleTransaction,
    Indent,
    IndentItem,
    PurchaseOrder,
    PurchaseOrderItem,
    GoodsReceivedNote,
    GRNItem,
]:
    admin.site.register(model)
