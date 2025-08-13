from django.urls import path
<<<<<<< HEAD

=======
>>>>>>> e582bea (django_refactor_test)
from . import views_ui

urlpatterns = [
    path("items/", views_ui.items_list, name="items_list"),
    path("items/table/", views_ui.items_table, name="items_table"),
<<<<<<< HEAD
    path("suppliers/", views_ui.suppliers_list, name="suppliers_list"),
    path("suppliers/table/", views_ui.suppliers_table, name="suppliers_table"),
=======
>>>>>>> e582bea (django_refactor_test)
]
