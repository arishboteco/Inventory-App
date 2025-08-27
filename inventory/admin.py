from django.contrib import admin

from .models import (
    Department,
    GoodsReceivedNote,
    GRNItem,
    Indent,
    IndentItem,
    Item,
    ItemDepartment,
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
    Department,
    ItemDepartment,
]:
    admin.site.register(model)
