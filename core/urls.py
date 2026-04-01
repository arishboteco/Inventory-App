from django.urls import path
from django.views.generic import RedirectView

from .views import ajax_dashboard_data

urlpatterns = [
    path(
        "interactive-dashboard/",
        RedirectView.as_view(url="/", permanent=True),
        name="interactive-dashboard",
    ),
    path("dashboard-data/", ajax_dashboard_data, name="ajax-dashboard-data"),
]
