import json
from decimal import Decimal

from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse
from django.shortcuts import redirect, render

from inventory.services import counts, dashboard_service, kpis


def root_view(request):
    """Render the home page or login form depending on authentication."""
    if request.user.is_authenticated:
        data = {
            "stock_value": kpis.stock_value(),
            "receipts": kpis.receipts_last_7_days(),
            "issues": kpis.issues_last_7_days(),
            "low_stock": kpis.low_stock_count(),
            "low_stock_items": kpis.low_stock_items(),
            "high_price_purchases": kpis.high_price_purchases(Decimal("0.1")),
            "pending_po_status": kpis.pending_po_status_counts(),
            "pending_indent_status": kpis.pending_indent_counts(),
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
        "low_stock_items": kpis.low_stock_items(),
        "stale_items": kpis.stale_items(),
        "high_price_purchases": kpis.high_price_purchases(Decimal("0.1")),
        "pending_po_status": kpis.pending_po_status_counts(),
        "pending_indent_status": kpis.pending_indent_counts(),
    }
    return render(request, "core/_kpi_cards.html", data)
