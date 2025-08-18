from django.urls import path

from .views.items import (
    ItemsListView,
    ItemsTableView,
    ItemCreateView,
    ItemEditView,
    ItemSuggestView,
    ItemsBulkUploadView,
)
from .views.suppliers import (
    SuppliersListView,
    SuppliersTableView,
    SupplierCreateView,
    SupplierEditView,
    SupplierToggleActiveView,
    SuppliersBulkUploadView,
    SuppliersBulkDeleteView,
)
from .views.stock import stock_movements, history_reports
from .views.indents import (
    IndentsListView,
    IndentsTableView,
    IndentCreateView,
    indent_detail,
    indent_update_status,
    indent_pdf,
)
from .views.purchase_orders import (
    purchase_orders_list,
    purchase_order_create,
    purchase_order_edit,
    purchase_order_detail,
    purchase_order_receive,
)
from .views.recipes import (
    RecipesListView,
    RecipeDetailView,
    RecipeComponentRowView,
)

urlpatterns = [
    path("items/", ItemsListView.as_view(), name="items_list"),
    path("items/table/", ItemsTableView.as_view(), name="items_table"),
    path("items/create/", ItemCreateView.as_view(), name="item_create"),
    path("items/<int:pk>/edit/", ItemEditView.as_view(), name="item_edit"),
    path("items/suggest/", ItemSuggestView.as_view(), name="item_suggest"),
    path("items/bulk-upload/", ItemsBulkUploadView.as_view(), name="items_bulk_upload"),

    path("suppliers/", SuppliersListView.as_view(), name="suppliers_list"),
    path("suppliers/table/", SuppliersTableView.as_view(), name="suppliers_table"),
    path("suppliers/create/", SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<int:pk>/edit/", SupplierEditView.as_view(), name="supplier_edit"),
    path("suppliers/<int:pk>/toggle/", SupplierToggleActiveView.as_view(), name="supplier_toggle_active"),
    path("suppliers/bulk-upload/", SuppliersBulkUploadView.as_view(), name="suppliers_bulk_upload"),
    path("suppliers/bulk-delete/", SuppliersBulkDeleteView.as_view(), name="suppliers_bulk_delete"),

    path("stock-movements/", stock_movements, name="stock_movements"),
    path("history-reports/", history_reports, name="history_reports"),

    path("indents/", IndentsListView.as_view(), name="indents_list"),
    path("indents/table/", IndentsTableView.as_view(), name="indents_table"),
    path("indents/create/", IndentCreateView.as_view(), name="indent_create"),
    path("indents/<int:pk>/", indent_detail, name="indent_detail"),
    path("indents/<int:pk>/status/<str:status>/", indent_update_status, name="indent_update_status"),
    path("indents/<int:pk>/pdf/", indent_pdf, name="indent_pdf"),

    path("purchase-orders/", purchase_orders_list, name="purchase_orders_list"),
    path("purchase-orders/create/", purchase_order_create, name="purchase_order_create"),
    path("purchase-orders/<int:pk>/edit/", purchase_order_edit, name="purchase_order_edit"),
    path("purchase-orders/<int:pk>/", purchase_order_detail, name="purchase_order_detail"),
    path("purchase-orders/<int:pk>/receive/", purchase_order_receive, name="purchase_order_receive"),

    path("recipes/", RecipesListView.as_view(), name="recipes_list"),
    path("recipes/<int:pk>/", RecipeDetailView.as_view(), name="recipe_detail"),
    path("recipes/<int:pk>/component-row/", RecipeComponentRowView.as_view(), name="recipe_component_row"),
]
