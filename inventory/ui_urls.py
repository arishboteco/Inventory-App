from django.urls import path

from .views.explore import explore, explore_export
from .views.goods_received import GRNDetailView, GRNListView, grn_export
from .views.indents import (
    IndentCreateView,
    IndentsListView,
    IndentsTableView,
    consolidate_indents,
    indent_detail,
    indent_pdf,
    indent_update_status,
    indents_consolidate,
    issue_indent,
)
from .views.items.detail import (
    ItemDeleteView,
    ItemDetailView,
    ItemEditView,
    ItemInlineUpdateView,
    ItemToggleActiveView,
)
from .views.items.list import (
    ItemSearchView,
    ItemsExportView,
    ItemsListView,
    ItemsTableView,
    distinct_values,
    item_meta,
)
from .views.items.stock import (
    ItemCreateHTMXView,
    ItemCreatePartialView,
    ItemsBulkUpdateView,
    ItemsBulkUploadView,
    PurchaseUnitsView,
    SubcategoriesView,
)
from .views.ml import ml_dashboard
from .views.purchase_orders import (
    PurchaseOrderCreatePartialView,
    PurchaseOrderEditPartialView,
    PurchaseOrderQuickCreatePartialView,
    PurchaseOrderReceivePartialView,
    PurchaseOrdersTableView,
    mark_ordered,
    purchase_order_create,
    purchase_order_detail,
    purchase_order_edit,
    purchase_order_receive,
    purchase_orders_list,
)
from .views.recipes import (
    RecipeCreatePartialView,
    RecipeEditPartialView,
    RecipesListView,
    RecipesTableView,
    recipe_create,
    recipe_detail,
)
from .views.stock import POSearchView, UserSearchView, history_reports, stock_movements
from .views.suppliers import (
    SupplierCreateView,
    SupplierEditView,
    SuppliersBulkDeleteView,
    SuppliersBulkUploadPartialView,
    SuppliersBulkUploadView,
    SuppliersCardView,
    SupplierSearchView,
    SuppliersListView,
    SuppliersTableView,
    SupplierToggleActiveView,
)
from .views.visualizations import visualizations
from .views.guides import WorkflowGuideView

urlpatterns = [
    path("explore/", explore, name="explore"),
    path("explore/export/", explore_export, name="explore_export"),
    path("items/", ItemsListView.as_view(), name="items_list"),
    path("items/table/", ItemsTableView.as_view(), name="items_table"),
    path("items/export/", ItemsExportView.as_view(), name="items_export"),
    path("items/distinct/<str:field>/", distinct_values, name="items_distinct"),
    path("items/create/", ItemCreateHTMXView.as_view(), name="item_create"),
    path(
        "items/create/partial/",
        ItemCreatePartialView.as_view(),
        name="item_create_partial",
    ),
    path(
        "items/<int:pk>/inline-update/",
        ItemInlineUpdateView.as_view(),
        name="item_inline_update",
    ),
    path("items/bulk/", ItemsBulkUpdateView.as_view(), name="items_bulk_update"),
    # Backward-compat name used in templates/tests
    path("items/upload/", ItemsBulkUploadView.as_view(), name="upload_csv"),
    path("items/<int:pk>/edit/", ItemEditView.as_view(), name="item_edit"),
    path("items/<int:pk>/delete/", ItemDeleteView.as_view(), name="item_delete"),
    path(
        "items/<int:pk>/toggle/",
        ItemToggleActiveView.as_view(),
        name="item_toggle_active",
    ),
    path("items/<int:pk>/", ItemDetailView.as_view(), name="item_detail"),
    path("items/search/", ItemSearchView.as_view(), name="item_search"),
    path("items/meta/<int:item_id>/", item_meta, name="item_meta"),
    path(
        "items/purchase-units/", PurchaseUnitsView.as_view(), name="get_purchase_units"
    ),
    path("items/subcategories/", SubcategoriesView.as_view(), name="get_subcategories"),
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
        "suppliers/bulk-upload/partial/",
        SuppliersBulkUploadPartialView.as_view(),
        name="suppliers_bulk_upload_partial",
    ),
    path(
        "suppliers/bulk-delete/",
        SuppliersBulkDeleteView.as_view(),
        name="suppliers_bulk_delete",
    ),
    path("suppliers/search/", SupplierSearchView.as_view(), name="supplier_search"),
    path("stock-movements/", stock_movements, name="stock_movements"),
    path("stock/users/search/", UserSearchView.as_view(), name="user_search"),
    path("stock/pos/search/", POSearchView.as_view(), name="po_search"),
    path("history-reports/", history_reports, name="history_reports"),
    path("visualizations/", visualizations, name="visualizations"),
    path("indents/", IndentsListView.as_view(), name="indents_list"),
    path("indents/table/", IndentsTableView.as_view(), name="indents_table"),
    path("indents/create/", IndentCreateView.as_view(), name="indent_create"),
    path("indents/<int:pk>/", indent_detail, name="indent_detail"),
    path("indents/<int:pk>/issue/", issue_indent, name="issue_indent"),
    path(
        "indents/<int:pk>/status/<str:status>/",
        indent_update_status,
        name="indent_update_status",
    ),
    path("indents/<int:pk>/pdf/", indent_pdf, name="indent_pdf"),
    path("indents/consolidate/", indents_consolidate, name="indents_consolidate"),
    path(
        "indents/consolidate/preview/",
        consolidate_indents,
        name="indents_consolidate_preview",
    ),
    path("purchase-orders/", purchase_orders_list, name="purchase_orders_list"),
    path(
        "purchase-orders/table/",
        PurchaseOrdersTableView.as_view(),
        name="purchase_orders_table",
    ),
    path(
        "purchase-orders/quick-create/partial/",
        PurchaseOrderQuickCreatePartialView.as_view(),
        name="purchase_order_quick_create_partial",
    ),
    path(
        "purchase-orders/create/", purchase_order_create, name="purchase_order_create"
    ),
    path(
        "purchase-orders/create/partial/",
        PurchaseOrderCreatePartialView.as_view(),
        name="purchase_order_create_partial",
    ),
    path(
        "purchase-orders/<int:pk>/edit/",
        purchase_order_edit,
        name="purchase_order_edit",
    ),
    path(
        "purchase-orders/<int:pk>/edit/partial/",
        PurchaseOrderEditPartialView.as_view(),
        name="purchase_order_edit_partial",
    ),
    path(
        "purchase-orders/<int:pk>/mark-ordered/",
        mark_ordered,
        name="purchase_order_mark_ordered",
    ),
    path(
        "purchase-orders/<int:pk>/", purchase_order_detail, name="purchase_order_detail"
    ),
    path(
        "purchase-orders/<int:pk>/receive/",
        purchase_order_receive,
        name="purchase_order_receive",
    ),
    path(
        "purchase-orders/<int:pk>/receive/partial/",
        PurchaseOrderReceivePartialView.as_view(),
        name="purchase_order_receive_partial",
    ),
    path("grns/", GRNListView.as_view(), name="grn_list"),
    path("grns/<int:pk>/export/", grn_export, name="grn_export"),
    path("grns/<int:pk>/", GRNDetailView.as_view(), name="grn_detail"),
    path("recipes/", RecipesListView.as_view(), name="recipes_list"),
    path("recipes/table/", RecipesTableView.as_view(), name="recipes_table"),
    path("recipes/create/", recipe_create, name="recipe_create"),
    path(
        "recipes/create/partial/",
        RecipeCreatePartialView.as_view(),
        name="recipe_create_partial",
    ),
    path("ml-dashboard/", ml_dashboard, name="ml_dashboard"),
    path(
        "recipes/<int:pk>/edit/partial/",
        RecipeEditPartialView.as_view(),
        name="recipe_edit_partial",
    ),
    path("recipes/<int:pk>/", recipe_detail, name="recipe_detail"),
    path("guides/workflow/", WorkflowGuideView.as_view(), name="workflow_guide"),
]
