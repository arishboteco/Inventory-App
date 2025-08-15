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
]
