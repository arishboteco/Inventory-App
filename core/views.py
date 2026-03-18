import json
import logging
from datetime import date, timedelta

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

    return redirect("/accounts/login/")


def password_reset_info_view(request):
    """Inform users to contact admin to reset their password."""
    return render(request, "registration/password_reset_info.html")


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
    """Return daily stock trend data.

    Prefers StockSnapshot (absolute stock levels) when available, falling back
    to StockTransaction daily aggregates when no snapshots exist.

    Args:
        item_id: Optional item ID to filter.
        supplier_id: Optional supplier ID to filter (via preferred_supplier FK on Item).
        start: Start date (inclusive).
        end: End date (inclusive).
        metric: "quantity" or "value".
    """
    # ── Try StockSnapshot first (absolute stock levels) ──────────────────
    try:
        from inventory.models.items import StockSnapshot

        qs = StockSnapshot.objects.all()
        if item_id:
            qs = qs.filter(item_id=item_id)
        if supplier_id:
            qs = qs.filter(item__preferred_supplier_id=supplier_id)
        if start:
            qs = qs.filter(snapshot_date__gte=start)
        if end:
            qs = qs.filter(snapshot_date__lte=end)

        if metric == "value":
            agg = qs.values("snapshot_date").annotate(total=Sum("value")).order_by("snapshot_date")
        else:
            agg = qs.values("snapshot_date").annotate(total=Sum("quantity")).order_by("snapshot_date")

        rows = list(agg)
        if rows:
            labels = [d["snapshot_date"].strftime("%Y-%m-%d") for d in rows]
            values = [float(d["total"] or 0) for d in rows]
            return labels, values
    except Exception:
        logger.debug("StockSnapshot unavailable, falling back to StockTransaction")

    # ── Fall back to StockTransaction daily aggregates ───────────────────
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


def _parse_date_range(request):
    """Extract and validate date range from request GET params.

    Supports preset ranges (7/30/90 days) and custom date_from / date_to.
    """
    range_days = request.GET.get("range", "30")
    date_from_raw = request.GET.get("date_from", "").strip()
    date_to_raw = request.GET.get("date_to", "").strip()
    today = timezone.now().date()

    if range_days == "custom" and (date_from_raw or date_to_raw):
        try:
            end = date.fromisoformat(date_to_raw) if date_to_raw else today
            start = date.fromisoformat(date_from_raw) if date_from_raw else end - timedelta(days=29)
        except ValueError:
            end = today
            start = today - timedelta(days=29)
    else:
        try:
            days = int(range_days)
        except (ValueError, TypeError):
            days = 30
        end = today
        start = end - timedelta(days=days - 1)

    return start, end


def interactive_dashboard(request):
    """Render interactive dashboard with filter controls for trend chart."""
    item_id = request.GET.get("item")
    supplier_id = request.GET.get("supplier")
    metric = request.GET.get("metric", "quantity")
    range_val = request.GET.get("range", "30")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    start, end = _parse_date_range(request)

    labels, values = _stock_trend_data(item_id, supplier_id, start, end, metric)
    context = DashboardContext(
        labels,
        values,
        items=Item.objects.filter(is_active=True),
        suppliers=Supplier.objects.filter(is_active=True),
    ).as_dict()
    context.update({
        "is_interactive": True,
        "page_title": "Interactive Dashboard – Inventory Pro",
        "current_title": "Interactive Dashboard",
        "selected_range": range_val,
        "selected_item": item_id or "",
        "selected_supplier": supplier_id or "",
        "selected_metric": metric,
        "date_from": date_from,
        "date_to": date_to,
    })
    return render(request, "core/dashboard.html", context)


def ajax_dashboard_data(request):
    """Return JSON chart data for the given filters."""
    item_id = request.GET.get("item")
    supplier_id = request.GET.get("supplier")
    metric = request.GET.get("metric", "quantity")
    start, end = _parse_date_range(request)

    labels, values = _stock_trend_data(item_id, supplier_id, start, end, metric)
    return JsonResponse({"labels": labels, "values": values})
