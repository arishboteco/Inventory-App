from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm

import json

from inventory.services import dashboard_service, kpis, counts


def root_view(request):
    """Render the home page or login form depending on authentication."""
    if request.user.is_authenticated:
        data = {
            "stock_value": kpis.stock_value(),
            "receipts": kpis.receipts_last_7_days(),
            "issues": kpis.issues_last_7_days(),
            "low_stock": kpis.low_stock_count(),
            "item_count": counts.item_count(),
            "supplier_count": counts.supplier_count(),
            "pending_po_count": counts.pending_po_count(),
        }
        return render(request, "core/home.html", data)

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("root")

    return render(request, "core/home.html", {"form": form})


def health_check(request):
    return HttpResponse("ok")


def dashboard(request):
    """Render dashboard shell; KPI cards are loaded asynchronously."""
    labels, values = kpis.stock_trend_last_7_days()
    context = {
        "low_stock": dashboard_service.get_low_stock_items(),
        "trend_labels": json.dumps(labels),
        "trend_values": json.dumps(values),
    }
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
