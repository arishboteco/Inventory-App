from django.urls import path
from . import views_ui

urlpatterns = [
    path("items/", views_ui.items_list, name="items_list"),
    path("items/table/", views_ui.items_table, name="items_table"),
    path("items/create/", views_ui.item_create, name="item_create"),
    path("items/<int:pk>/edit/", views_ui.item_edit, name="item_edit"),
    path("items/bulk-upload/", views_ui.items_bulk_upload, name="items_bulk_upload"),

    path("suppliers/", views_ui.suppliers_list, name="suppliers_list"),
    path("suppliers/table/", views_ui.suppliers_table, name="suppliers_table"),
    path("suppliers/create/", views_ui.supplier_create, name="supplier_create"),
    path("suppliers/<int:pk>/edit/", views_ui.supplier_edit, name="supplier_edit"),
    path(
        "suppliers/<int:pk>/toggle/",
        views_ui.supplier_toggle_active,
        name="supplier_toggle_active",
    ),
    path(
        "suppliers/bulk-upload/",
        views_ui.suppliers_bulk_upload,
        name="suppliers_bulk_upload",
    ),
    path(
        "suppliers/bulk-delete/",
        views_ui.suppliers_bulk_delete,
        name="suppliers_bulk_delete",
    ),
    path("stock-movements/", views_ui.stock_movements, name="stock_movements"),
    path("history-reports/", views_ui.history_reports, name="history_reports"),

    path("indents/", views_ui.indents_list, name="indents_list"),
    path("indents/table/", views_ui.indents_table, name="indents_table"),
    path("indents/create/", views_ui.indent_create, name="indent_create"),
    path("indents/<int:pk>/", views_ui.indent_detail, name="indent_detail"),
    path(
        "indents/<int:pk>/status/<str:status>/",
        views_ui.indent_update_status,
        name="indent_update_status",
    ),
    path("indents/<int:pk>/pdf/", views_ui.indent_pdf, name="indent_pdf"),

    path("purchase-orders/", views_ui.purchase_orders_list, name="purchase_orders_list"),
    path(
        "purchase-orders/create/",
        views_ui.purchase_order_create,
        name="purchase_order_create",
    ),
    path(
        "purchase-orders/<int:pk>/edit/",
        views_ui.purchase_order_edit,
        name="purchase_order_edit",
    ),
    path(
        "purchase-orders/<int:pk>/",
        views_ui.purchase_order_detail,
        name="purchase_order_detail",
    ),
    path(
        "purchase-orders/<int:pk>/receive/",
        views_ui.purchase_order_receive,
        name="purchase_order_receive",
    ),
]
