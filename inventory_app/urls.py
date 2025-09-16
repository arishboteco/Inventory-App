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

from django.conf import settings
from django.conf.urls.static import static as serve_static
from django.contrib import admin
from django.templatetags.static import static
from django.urls import include, path
from django.views.generic.base import RedirectView

from core.views import dashboard_kpis, health_check, root_view

urlpatterns = [
    path("admin/", admin.site.urls),
    # Favicon for browsers that hit /favicon.ico directly
    path(
        "favicon.ico",
        RedirectView.as_view(
            url=static("img/favicon.svg"),
            permanent=True,
        ),
    ),
    path(
        "login/",
        RedirectView.as_view(pattern_name="root", permanent=False),
        name="login",
    ),
    path("", root_view, name="root"),
    path("kpis/", dashboard_kpis, name="dashboard-kpis"),
    path("healthz", health_check, name="health-check"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("core.urls")),
    path("api/", include("inventory.urls")),  # DRF API
    path("", include("inventory.ui_urls")),  # HTML UI routes
]

# Serve uploaded media in development
if settings.DEBUG:
    urlpatterns += serve_static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
