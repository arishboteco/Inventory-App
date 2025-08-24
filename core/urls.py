from django.urls import path

from .views import ajax_dashboard_data, interactive_dashboard

urlpatterns = [
    path("dashboard/interactive/", interactive_dashboard, name="interactive-dashboard"),
    path("dashboard/data/", ajax_dashboard_data, name="ajax-dashboard-data"),
]
