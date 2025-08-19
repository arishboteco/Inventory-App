from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from inventory.services import dashboard_service


def root_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "core/home.html")


def health_check(request):
    return HttpResponse("ok")


@login_required
def dashboard(request):
    low_stock = dashboard_service.get_low_stock_items()
    return render(request, "core/dashboard.html", {"low_stock": low_stock})
