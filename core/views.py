import json
from decimal import Decimal

from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_date
from django.db.models import Sum
from django.db.models.functions import TruncDate

from inventory.models import Item, Supplier, StockTransaction, PurchaseOrder
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


def _stock_trend_data(item_id=None, supplier_id=None, start=None, end=None):
    """Return stock transaction totals grouped by day."""
    qs = StockTransaction.objects.all()
    if item_id:
        qs = qs.filter(item_id=item_id)
    if supplier_id:
        po_ids = PurchaseOrder.objects.filter(supplier_id=supplier_id).values_list(
            "po_id", flat=True
        )
        qs = qs.filter(related_po_id__in=po_ids)
    if start:
        qs = qs.filter(transaction_date__date__gte=start)
    if end:
        qs = qs.filter(transaction_date__date__lte=end)

    data = (
        qs.annotate(day=TruncDate("transaction_date"))
        .values("day")
        .order_by("day")
        .annotate(total=Sum("quantity_change"))
    )
    labels = [d["day"].strftime("%Y-%m-%d") for d in data]
    values = [float(d["total"]) for d in data]
    return labels, values


def interactive_dashboard(request):
    """Render dashboard with filter controls for asynchronous charts."""
    item_id = request.GET.get("item")
    supplier_id = request.GET.get("supplier")
    start = parse_date(request.GET.get("start")) if request.GET.get("start") else None
    end = parse_date(request.GET.get("end")) if request.GET.get("end") else None

    labels, values = _stock_trend_data(item_id, supplier_id, start, end)
    context = {
        "low_stock": dashboard_service.get_low_stock_items(),
        "trend_labels": json.dumps(labels),
        "trend_values": json.dumps(values),
        "items": Item.objects.filter(is_active=True),
        "suppliers": Supplier.objects.filter(is_active=True),
    }
    return render(request, "core/dashboard.html", context)


def ajax_dashboard_data(request):
    """Return JSON data for dashboard charts based on filters."""
    item_id = request.GET.get("item")
    supplier_id = request.GET.get("supplier")
    start = parse_date(request.GET.get("start")) if request.GET.get("start") else None
    end = parse_date(request.GET.get("end")) if request.GET.get("end") else None

    labels, values = _stock_trend_data(item_id, supplier_id, start, end)
    return JsonResponse({"labels": labels, "values": values})
