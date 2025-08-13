from django.urls import path

from .views_ui import items_list, items_table

urlpatterns = [
    path("items/", items_list, name="items_list"),
    path("items/table/", items_table, name="items_table"),
]
