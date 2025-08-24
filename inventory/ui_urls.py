from django.urls import path

from .views.goods_received import GRNDetailView, GRNListView, grn_export
from .views.indents import (
    IndentCreateView,
    IndentsListView,
    IndentsTableView,
    indent_detail,
    indent_pdf,
    indent_update_status,
)
from .views.items import (
    ItemCreateView,
    ItemDeleteView,
    ItemDetailView,
    ItemEditView,
    ItemsBulkUploadView,
    ItemSearchView,
    ItemsExportView,
    ItemsListView,
    ItemsTableView,
    ItemToggleActiveView,
)
from .views.purchase_orders import (
    purchase_order_create,
    purchase_order_detail,
    purchase_order_edit,
    purchase_order_receive,
    purchase_orders_list,
)
from .views.recipes import RecipesListView, recipe_create, recipe_detail
from .views.ml import ml_dashboard
from .views.stock import history_reports, stock_movements
from .views.visualizations import visualizations
from .views.suppliers import (
    SupplierCreateView,
    SupplierEditView,
    SuppliersBulkDeleteView,
    SuppliersBulkUploadView,
    SuppliersCardView,
    SupplierSearchView,
    SuppliersListView,
    SuppliersTableView,
    SupplierToggleActiveView,
)

urlpatterns = [
    path("items/", ItemsListView.as_view(), name="items_list"),
    path("items/table/", ItemsTableView.as_view(), name="items_table"),
    path("items/export/", ItemsExportView.as_view(), name="items_export"),
    path("items/create/", ItemCreateView.as_view(), name="item_create"),
    path("items/<int:pk>/edit/", ItemEditView.as_view(), name="item_edit"),
    path("items/<int:pk>/delete/", ItemDeleteView.as_view(), name="item_delete"),
    path(
        "items/<int:pk>/toggle/",
        ItemToggleActiveView.as_view(),
        name="item_toggle_active",
    ),
    path("items/<int:pk>/", ItemDetailView.as_view(), name="item_detail"),
    path("items/search/", ItemSearchView.as_view(), name="item_search"),
    path("items/bulk-upload/", ItemsBulkUploadView.as_view(), name="items_bulk_upload"),
    path("suppliers/", SuppliersListView.as_view(), name="suppliers_list"),
    path("suppliers/table/", SuppliersTableView.as_view(), name="suppliers_table"),
    path("suppliers/cards/", SuppliersCardView.as_view(), name="suppliers_cards"),
    path("suppliers/create/", SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<int:pk>/edit/", SupplierEditView.as_view(), name="supplier_edit"),
    path(
        "suppliers/<int:pk>/toggle/",
        SupplierToggleActiveView.as_view(),
        name="supplier_toggle_active",
    ),
    path(
        "suppliers/bulk-upload/",
        SuppliersBulkUploadView.as_view(),
        name="suppliers_bulk_upload",
    ),
    path(
        "suppliers/bulk-delete/",
        SuppliersBulkDeleteView.as_view(),
        name="suppliers_bulk_delete",
    ),
    path("suppliers/search/", SupplierSearchView.as_view(), name="supplier_search"),
    path("stock-movements/", stock_movements, name="stock_movements"),
    path("history-reports/", history_reports, name="history_reports"),
    path("visualizations/", visualizations, name="visualizations"),
    path("indents/", IndentsListView.as_view(), name="indents_list"),
    path("indents/table/", IndentsTableView.as_view(), name="indents_table"),
    path("indents/create/", IndentCreateView.as_view(), name="indent_create"),
    path("indents/<int:pk>/", indent_detail, name="indent_detail"),
    path(
        "indents/<int:pk>/status/<str:status>/",
        indent_update_status,
        name="indent_update_status",
    ),
    path("indents/<int:pk>/pdf/", indent_pdf, name="indent_pdf"),
    path("purchase-orders/", purchase_orders_list, name="purchase_orders_list"),
    path(
        "purchase-orders/create/", purchase_order_create, name="purchase_order_create"
    ),
    path(
        "purchase-orders/<int:pk>/edit/",
        purchase_order_edit,
        name="purchase_order_edit",
    ),
    path(
        "purchase-orders/<int:pk>/", purchase_order_detail, name="purchase_order_detail"
    ),
    path(
        "purchase-orders/<int:pk>/receive/",
        purchase_order_receive,
        name="purchase_order_receive",
    ),
    path("grns/", GRNListView.as_view(), name="grn_list"),
    path("grns/<int:pk>/export/", grn_export, name="grn_export"),
    path("grns/<int:pk>/", GRNDetailView.as_view(), name="grn_detail"),
    path("recipes/", RecipesListView.as_view(), name="recipes_list"),
    path("recipes/create/", recipe_create, name="recipe_create"),
    path("ml-dashboard/", ml_dashboard, name="ml_dashboard"),
    path("recipes/<int:pk>/", recipe_detail, name="recipe_detail"),
]
