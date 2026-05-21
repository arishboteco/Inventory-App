from django.contrib import admin

from .models import (
    Category,
    ChefBulletin,
    Department,
    GoodsReceivedNote,
    GRNItem,
    Indent,
    IndentItem,
    Item,
    ItemDepartment,
    POSMenuItemMapping,
    PurchaseOrder,
    PurchaseOrderItem,
    Recipe,
    RecipeItem,
    RecoveryAction,
    SaleTransaction,
    SavingsLedger,
    StockTransaction,
    SubCategory,
    Supplier,
    TrialRecipeVersion,
    Unit,
    VendorItemPrice,
)

for model in [
    Item,
    Supplier,
    StockTransaction,
    Recipe,
    RecipeItem,
    SaleTransaction,
    POSMenuItemMapping,
    Indent,
    IndentItem,
    PurchaseOrder,
    PurchaseOrderItem,
    GoodsReceivedNote,
    GRNItem,
    SavingsLedger,
    VendorItemPrice,
    ChefBulletin,
    TrialRecipeVersion,
    RecoveryAction,
    Department,
    ItemDepartment,
]:
    admin.site.register(model)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("category_id", "category", "sub_category")
    search_fields = ("category", "sub_category")
    list_filter = ("category",)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "name")
    search_fields = ("name", "category__category")
    list_filter = ("category",)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("unit_id", "purchase_unit", "base_unit", "conversion_factor")
    search_fields = ("purchase_unit", "base_unit")
    list_filter = ("base_unit",)
