from django.http import HttpResponse
from django.shortcuts import render

from inventory.services import dashboard_service, kpis


def root_view(request):
    """Render the home page."""
    return render(request, "core/home.html")


def health_check(request):
    return HttpResponse("ok")


def dashboard(request):
    """Render dashboard shell; KPI cards are loaded asynchronously."""
    context = {"low_stock": dashboard_service.get_low_stock_items()}
    return render(request, "core/dashboard.html", context)


def dashboard_kpis(request):
    """HTMX endpoint returning KPI card values."""
    data = {
        "stock_value": kpis.stock_value(),
        "receipts": kpis.receipts_last_7_days(),
        "issues": kpis.issues_last_7_days(),
        "low_stock": kpis.low_stock_count(),
    }
    return render(request, "core/_kpi_cards.html", data)
