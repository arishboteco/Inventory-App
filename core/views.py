import json
import logging
from datetime import timedelta

from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from inventory.models import Item, PurchaseOrder, StockTransaction, Supplier
from inventory.services import counts, kpis

from .viewmodels import DashboardContext

logger = logging.getLogger(__name__)


def root_view(request):
    """Render login form or dashboard depending on authentication."""
    logger.debug("User authenticated: %s", request.user.is_authenticated)
    if request.user.is_authenticated:
        end = timezone.now().date()
        start = end - timedelta(days=29)
        labels, values = _stock_trend_data(start=start, end=end)
        context = {
            "item_count": counts.item_count(),
            "low_stock": kpis.low_stock_count(),
            "supplier_count": counts.supplier_count(),
            "pending_indents": sum(kpis.pending_indent_counts().values()),
            "trend_labels": json.dumps(labels),
            "trend_values": json.dumps(values),
            "items": Item.objects.filter(is_active=True),
            "suppliers": Supplier.objects.filter(is_active=True),
            "list_url": reverse("root"),
            "list_title": "Dashboard",
            "current_title": "Dashboard",
        }
        return render(request, "core/dashboard.html", context)

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("root")
    return render(request, "core/dashboard.html", {"form": form})


def health_check(request):
    return HttpResponse("ok")


def dashboard_kpis(request):
    """HTMX endpoint returning KPI card values."""
    data = {
        "items": counts.item_count(),
        "low_stock": kpis.low_stock_count(),
        "suppliers": counts.supplier_count(),
        "pending_indents": sum(kpis.pending_indent_counts().values()),
    }
    return render(request, "core/_kpi_cards.html", data)


def _stock_trend_data(
    item_id=None, supplier_id=None, start=None, end=None, metric="quantity"
):
    """Return stock transaction totals grouped by day.

    Args:
        item_id: Optional item identifier to filter by item.
        supplier_id: Optional supplier identifier to filter by supplier.
        start: Start date for filtering (inclusive).
        end: End date for filtering (inclusive).
        metric: "quantity" to aggregate quantities or "value" for monetary value.
    """

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

    annotation = {"total": Sum("quantity_change")}
    if metric == "value":
        annotation["total"] = Sum(
            ExpressionWrapper(
                F("quantity_change") * Coalesce(F("item__last_purchase_price"), 0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        qs = qs.select_related("item")

    data = (
        qs.annotate(day=TruncDate("transaction_date"))
        .values("day")
        .order_by("day")
        .annotate(**annotation)
    )
    labels = [d["day"].strftime("%Y-%m-%d") for d in data]
    values = [float(d["total"]) for d in data]
    return labels, values


def interactive_dashboard(request):
    """Render dashboard with filter controls for asynchronous charts."""
    item_id = request.GET.get("item")
    supplier_id = request.GET.get("supplier")
    metric = request.GET.get("metric", "quantity")
    days = int(request.GET.get("range", 30))
    end = timezone.now().date()
    start = end - timedelta(days=days - 1)

    labels, values = _stock_trend_data(item_id, supplier_id, start, end, metric)
    context = DashboardContext(
        labels,
        values,
        items=Item.objects.filter(is_active=True),
        suppliers=Supplier.objects.filter(is_active=True),
    ).as_dict()
    return render(request, "core/dashboard.html", context)


def ajax_dashboard_data(request):
    """Return JSON data for dashboard charts based on filters."""
    item_id = request.GET.get("item")
    supplier_id = request.GET.get("supplier")
    metric = request.GET.get("metric", "quantity")
    days = int(request.GET.get("range", 30))
    end = timezone.now().date()
    start = end - timedelta(days=days - 1)

    labels, values = _stock_trend_data(item_id, supplier_id, start, end, metric)
    return JsonResponse({"labels": labels, "values": values})
