from django.urls import path

from . import views_ui

urlpatterns = [
    path("items/", views_ui.items_list, name="items_list"),
    path("items/table/", views_ui.items_table, name="items_table"),
]
