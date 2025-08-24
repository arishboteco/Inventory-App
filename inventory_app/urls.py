"""
URL configuration for inventory_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from core.views import root_view, health_check, dashboard, dashboard_kpis

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", root_view, name="login"),
    path("", root_view, name="root"),
    path("dashboard/", dashboard, name="dashboard"),
    path("dashboard/kpis/", dashboard_kpis, name="dashboard-kpis"),
    path("healthz", health_check, name="health-check"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("api/", include("inventory.urls")),   # DRF API
    path("", include("inventory.ui_urls")),    # HTML UI routes
]
