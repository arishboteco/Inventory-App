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
]
