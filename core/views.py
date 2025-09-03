import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from inventory.models import Item, PurchaseOrder, StockTransaction, Supplier
from inventory.services import counts, kpis
from inventory.services.stock_utils import get_low_stock_items

from .viewmodels import DashboardContext

logger = logging.getLogger(__name__)


def root_view(request):
    """Render the home page or login form depending on authentication."""
    logger.debug("User authenticated: %s", request.user.is_authenticated)
    if request.user.is_authenticated:
        # Optionally bypass cache during tests
        bypass_cache = getattr(settings, "DISABLE_DASHBOARD_CACHE", False)
        cache_key = "dashboard_data_v2"
        data = None if bypass_cache else cache.get(cache_key)

        if data is None:
            data = {
                "stock_value": kpis.stock_value_on_hand(),
                "receipts": kpis.receipts_last_7_days(),
                "issues": kpis.issues_last_7_days(),
                "low_stock": kpis.low_stock_count(),
                "low_stock_items": get_low_stock_items(),
                "high_price_purchases": kpis.high_price_purchases(Decimal("0.1")),
                "pending_po_status": kpis.pending_po_status_counts(),
                "pending_indent_status": kpis.pending_indent_counts(),
                "item_count": counts.item_count(),
                "supplier_count": counts.supplier_count(),
                "pending_po_count": counts.pending_po_count(),
            }
            if not bypass_cache:
                cache.set(cache_key, data, 300)  # Cache for 5 minutes

        return render(request, "core/home.html", data)

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST":
        logger.debug("POST data: %s", request.POST)
        logger.debug("Form is valid: %s", form.is_valid())
        if not form.is_valid():
            logger.debug("Form errors: %s", form.errors)
        if form.is_valid():
            user = form.get_user()
            logger.info("Logging in user: %s", user.username)
            login(request, user)
            logger.debug(
                "User authenticated after login: %s",
                request.user.is_authenticated,
            )
            return redirect("root")

    return render(request, "core/home.html", {"form": form})


def health_check(request):
    return HttpResponse("ok")


def dashboard(request):
    """Render dashboard shell; KPI cards are loaded asynchronously."""
    labels, values = kpis.stock_trend_last_7_days()
    context = DashboardContext(labels, values).as_dict()
    return render(request, "core/dashboard.html", context)


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
