from django.urls import path
from django.views.generic import RedirectView

from .views.chef_bulletins import (
    chef_bulletin_decision,
    chef_bulletin_detail,
    chef_bulletins_list,
)
from .views.goods_received import (
    GRNCreateView,
    GRNDetailView,
    GRNListView,
    create_adhoc_grn,
    grn_export,
)
from .views.guides import WorkflowGuideView
from .views.indents import (
    IndentCreateView,
    IndentsListView,
    IndentsTableView,
    IndentUpdateView,
    consolidate_indents,
    generate_low_stock_indent,
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
    PurchaseOrderReceivePartialView,
    PurchaseOrdersCardsView,
    PurchaseOrdersExportView,
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
    RecipeDeleteView,
    RecipeEditPartialView,
    RecipesListView,
    RecipesTableView,
    RecipeViewPartialView,
    food_cost_report,
    recipe_create,
    recipe_create_indent,
    recipe_detail,
    recipe_meta,
)
from .views.recovery import (
    recovery_action_detail,
    recovery_action_status,
    recovery_actions_list,
    savings_ledger_list,
    vendor_prices_list,
)
from .views.sales import pos_sales_import
from .views.settings import change_password_view, profile_edit_view, settings_view
from .views.stock import POSearchView, UserSearchView, history_reports, stock_movements
from .views.stock_take import (
    create_stock_take,
    stock_take_count,
    stock_take_list,
    stock_take_review,
)
from .views.suppliers import (
    SupplierCreateView,
    SupplierDeleteView,
    SupplierDetailView,
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
from .views.variance import variance_report
from .views.visualizations import visualizations

urlpatterns = [
    path(
        "explore/", RedirectView.as_view(url="/items/", permanent=True), name="explore"
    ),
    path(
        "explore/export/",
        RedirectView.as_view(url="/items/", permanent=True),
        name="explore_export",
    ),
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
    path("suppliers/<int:pk>/", SupplierDetailView.as_view(), name="supplier_detail"),
    path(
        "suppliers/<int:pk>/delete/",
        SupplierDeleteView.as_view(),
        name="supplier_delete",
    ),
    path("stock-movements/", stock_movements, name="stock_movements"),
    path("stock/users/search/", UserSearchView.as_view(), name="user_search"),
    path("stock/pos/search/", POSearchView.as_view(), name="po_search"),
    path("history-reports/", history_reports, name="history_reports"),
    path("stock-takes/", stock_take_list, name="stock_take_list"),
    path("stock-takes/new/", create_stock_take, name="stock_take_start"),
    path("stock-takes/<int:pk>/count/", stock_take_count, name="stock_take_count"),
    path("stock-takes/<int:pk>/review/", stock_take_review, name="stock_take_review"),
    path("visualizations/", visualizations, name="visualizations"),
    path("indents/", IndentsListView.as_view(), name="indents_list"),
    path("indents/table/", IndentsTableView.as_view(), name="indents_table"),
    path("indents/create/", IndentCreateView.as_view(), name="indent_create"),
    path("indents/<int:pk>/", indent_detail, name="indent_detail"),
    path("indents/<int:pk>/update/", IndentUpdateView.as_view(), name="indent_update"),
    path("indents/<int:pk>/issue/", issue_indent, name="issue_indent"),
    path(
        "indents/<int:pk>/status/<str:status>/",
        indent_update_status,
        name="indent_update_status",
    ),
    path("indents/<int:pk>/pdf/", indent_pdf, name="indent_pdf"),
    path(
        "indents/generate-from-low-stock/",
        generate_low_stock_indent,
        name="low_stock_indent",
    ),
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
        "purchase-orders/cards/",
        PurchaseOrdersCardsView.as_view(),
        name="purchase_orders_cards",
    ),
    path(
        "purchase-orders/export/",
        PurchaseOrdersExportView.as_view(),
        name="purchase_orders_export",
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
    path("grns/create/", GRNCreateView.as_view(), name="grn_create"),
    path("grns/create/adhoc/", create_adhoc_grn, name="grn_create_adhoc"),
    path("grns/<int:pk>/export/", grn_export, name="grn_export"),
    path("grns/<int:pk>/", GRNDetailView.as_view(), name="grn_detail"),
    path("savings-ledger/", savings_ledger_list, name="savings_ledger_list"),
    path("vendor-prices/", vendor_prices_list, name="vendor_prices_list"),
    path("recovery-actions/", recovery_actions_list, name="recovery_actions_list"),
    path(
        "recovery-actions/<int:action_id>/",
        recovery_action_detail,
        name="recovery_action_detail",
    ),
    path(
        "recovery-actions/<int:action_id>/status/",
        recovery_action_status,
        name="recovery_action_status",
    ),
    path("pos-sales/", pos_sales_import, name="pos_sales_import"),
    path("variance-report/", variance_report, name="variance_report"),
    path("chef-bulletins/", chef_bulletins_list, name="chef_bulletins_list"),
    path(
        "chef-bulletins/<int:bulletin_id>/",
        chef_bulletin_detail,
        name="chef_bulletin_detail",
    ),
    path(
        "chef-bulletins/<int:bulletin_id>/decision/",
        chef_bulletin_decision,
        name="chef_bulletin_decision",
    ),
    path("recipes/", RecipesListView.as_view(), name="recipes_list"),
    path("recipes/table/", RecipesTableView.as_view(), name="recipes_table"),
    path("recipes/food-cost-report/", food_cost_report, name="food_cost_report"),
    path(
        "recipes/meta/<int:recipe_id>/",
        recipe_meta,
        name="recipe_meta",
    ),
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
    path(
        "recipes/<int:pk>/view/partial/",
        RecipeViewPartialView.as_view(),
        name="recipe_view_partial",
    ),
    path(
        "recipes/<int:pk>/create-indent/",
        recipe_create_indent,
        name="recipe_create_indent",
    ),
    path("recipes/<int:pk>/delete/", RecipeDeleteView.as_view(), name="recipe_delete"),
    path("recipes/<int:pk>/", recipe_detail, name="recipe_detail"),
    path("guides/workflow/", WorkflowGuideView.as_view(), name="workflow_guide"),
    path("settings/", settings_view, name="settings"),
    path("profile/edit/", profile_edit_view, name="profile-edit"),
    path("profile/change-password/", change_password_view, name="change-password"),
]
