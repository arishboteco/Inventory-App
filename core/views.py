import json
import logging
from datetime import timedelta

from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from inventory.models import Indent, Item, PurchaseOrder, StockTransaction
from inventory.models.enums import PurchaseOrderStatus
from inventory.models.stock_take import StockTake
from inventory.services import dashboard_kpis as dkpis
from inventory.services import kpis
from inventory.services.dashboard_bundle import (
    get_cached_dashboard_bundle,
    get_kpi_subset_for_partial,
    range_days_from_start_end,
)
from inventory.services.recovery_dashboard_service import build_owner_money_dashboard
from inventory.services.stock_utils import get_low_stock_items

logger = logging.getLogger(__name__)


def _stock_trend_data(item_id, start, end, metric="quantity"):
    """Return daily stock movement trend data for compatibility reports/tests."""
    value_expr = F("quantity_change")
    if metric == "value":
        value_expr = ExpressionWrapper(
            F("quantity_change") * Coalesce(F("item__last_purchase_price"), 0),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    rows = (
        StockTransaction.objects.filter(
            item_id=item_id,
            transaction_date__date__gte=start,
            transaction_date__date__lte=end,
        )
        .annotate(day=TruncDate("transaction_date"))
        .values("day")
        .annotate(
            total=Coalesce(
                Sum(value_expr),
                0,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
        .order_by("day")
    )
    labels = []
    values = []
    for row in rows:
        labels.append(row["day"].strftime("%Y-%m-%d"))
        values.append(float(row["total"] or 0))
    return labels, values


def _greeting(user):
    hour = timezone.localtime().hour
    if hour < 12:
        prefix = "Good morning"
    elif hour < 18:
        prefix = "Good afternoon"
    else:
        prefix = "Good evening"
    name = user.first_name or user.username or ""
    return f"{prefix}, {name}" if name else prefix


def _build_alerts(*, actual_fc_trailing_30d=None):
    """Build a list of alert dicts for the dashboard attention panel.

    Pass ``actual_fc_trailing_30d`` when already computed (e.g. from dashboard
    bundle for a 30-day range) to avoid duplicate food-cost queries.
    """
    alerts = []

    try:
        pending = Indent.objects.filter(status="SUBMITTED").count()
        if pending:
            alerts.append(
                {
                    "icon": "clipboard-document-list",
                    "label": f"{pending} indent{'s' if pending != 1 else ''} awaiting approval",
                    "url": reverse("indents_list") + "?status=SUBMITTED",
                    "color": "warning",
                }
            )
    except Exception:
        pass

    try:
        end = timezone.now().date()
        if actual_fc_trailing_30d is not None:
            actual_fc = actual_fc_trailing_30d
        else:
            actual_fc = dkpis.actual_food_cost_pct(end - timedelta(days=29), end)
        if actual_fc and actual_fc > 35:
            alerts.append(
                {
                    "icon": "exclamation-triangle",
                    "label": f"Food cost at {actual_fc}% — above 35% target",
                    "url": reverse("food_cost_report"),
                    "color": "danger",
                }
            )
    except Exception:
        pass

    try:
        low = kpis.low_stock_count()
        if low:
            alerts.append(
                {
                    "icon": "exclamation-triangle",
                    "label": f"{low} item{'s' if low != 1 else ''} below reorder point",
                    "url": reverse("items_list") + "?stock_status=low",
                    "color": "danger",
                }
            )
    except Exception:
        pass

    try:
        draft_pos = PurchaseOrder.objects.filter(
            status=PurchaseOrderStatus.DRAFT
        ).count()
        if draft_pos:
            alerts.append(
                {
                    "icon": "document-text",
                    "label": f"{draft_pos} draft PO{'s' if draft_pos != 1 else ''} not yet sent",
                    "url": reverse("purchase_orders_list") + "?status=DRAFT",
                    "color": "info",
                }
            )
    except Exception:
        pass

    try:
        sent_pos = PurchaseOrder.objects.filter(status=PurchaseOrderStatus.SENT).count()
        if sent_pos:
            alerts.append(
                {
                    "icon": "inbox-arrow-down",
                    "label": f"{sent_pos} PO{'s' if sent_pos != 1 else ''} awaiting delivery",
                    "url": reverse("purchase_orders_list") + "?status=SENT",
                    "color": "info",
                }
            )
    except Exception:
        pass

    try:
        open_takes = StockTake.objects.exclude(status="COMPLETED").count()
        if open_takes:
            alerts.append(
                {
                    "icon": "clipboard-document-check",
                    "label": f"{open_takes} open stock take{'s' if open_takes != 1 else ''}",
                    "url": reverse("stock_take_list"),
                    "color": "warning",
                }
            )
    except Exception:
        pass

    return alerts


def root_view(request):
    """Render login form or dashboard depending on authentication."""
    if request.user.is_authenticated:
        end = timezone.now().date()
        range_days = int(request.GET.get("range", "30"))
        start = end - timedelta(days=range_days - 1)
        bundle = get_cached_dashboard_bundle(range_days, end)
        owner_money = build_owner_money_dashboard(start, end, bundle)
        opening = owner_money["opening_stock"]
        closing = owner_money["closing_stock"]
        purchases = owner_money["purchases"]
        consumption = owner_money["actual_food_cost"]
        cons_delta = bundle["consumption_delta"]
        revenue = owner_money["sales_revenue"]
        actual_fc = owner_money["current_food_cost_pct"]
        ideal_fc = owner_money["target_food_cost_pct"]
        wastage = owner_money["wastage"]
        waste_delta = bundle["wastage_delta"]
        trend_labels = bundle["trend_labels"]
        trend_consumption = bundle["trend_consumption"]
        trend_wastage = bundle["trend_wastage"]

        alert_fc_30 = actual_fc if range_days == 30 else None
        if alert_fc_30 is None:
            try:
                alert_fc_30 = dkpis.actual_food_cost_pct(end - timedelta(days=29), end)
            except Exception:
                alert_fc_30 = None

        active_items = Item.objects.filter(is_active=True).count()
        low_stock_count = kpis.low_stock_count()
        low_stock_pct = (
            round(low_stock_count / active_items * 100, 1) if active_items else 0
        )
        stock_value = float(closing) if closing else 0
        try:
            fastest_movers = kpis.fastest_movers_last_7_days()
        except Exception:
            fastest_movers = []

        context = {
            "greeting": _greeting(request.user),
            "selected_range": str(range_days),
            "opening_stock": opening,
            "closing_stock": closing,
            "purchases": purchases,
            "consumption": consumption,
            "consumption_delta": cons_delta,
            "sales_revenue": revenue,
            "actual_fc": actual_fc,
            "ideal_fc": ideal_fc,
            **owner_money,
            "wastage": wastage,
            "wastage_delta": waste_delta,
            "trend_labels": json.dumps(trend_labels),
            "trend_consumption": json.dumps(trend_consumption),
            "trend_wastage": json.dumps(trend_wastage),
            "active_items": active_items,
            "low_stock_count": low_stock_count,
            "low_stock_pct": low_stock_pct,
            "stock_value": stock_value,
            "fastest_movers": fastest_movers,
            "alerts": _build_alerts(actual_fc_trailing_30d=alert_fc_30),
            "low_stock_items": get_low_stock_items()[:5],
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
    """HTMX endpoint returning KPI card values (shared cache with dashboard bundle)."""
    end = timezone.now().date()
    range_days = int(request.GET.get("range", "30"))
    start = end - timedelta(days=range_days - 1)
    bundle = get_cached_dashboard_bundle(range_days, end)
    data = get_kpi_subset_for_partial(bundle)
    owner_money = build_owner_money_dashboard(start, end, bundle)
    data.update(owner_money)
    data["consumption"] = owner_money["actual_food_cost"]
    data["actual_fc"] = owner_money["current_food_cost_pct"]
    data["ideal_fc"] = owner_money["target_food_cost_pct"]
    return render(request, "core/_kpi_cards.html", data)


def _parse_date_range(request):
    """Extract and validate date range from request GET params."""
    range_days = request.GET.get("range", "30")
    today = timezone.now().date()
    try:
        days = int(range_days)
    except (ValueError, TypeError):
        days = 30
    end = today
    start = end - timedelta(days=days - 1)
    return start, end


def interactive_dashboard(request):
    """Render interactive dashboard with filter controls for trend chart."""
    return root_view(request)


def ajax_dashboard_data(request):
    """Return JSON chart data for the given filters."""
    start, end = _parse_date_range(request)
    item_id = request.GET.get("item")
    supplier_id = request.GET.get("supplier")
    metric = request.GET.get("metric", "quantity")
    if item_id or supplier_id:
        qs = StockTransaction.objects.filter(
            transaction_date__date__gte=start,
            transaction_date__date__lte=end,
        )
        if item_id:
            qs = qs.filter(item_id=item_id)
        if supplier_id:
            qs = qs.filter(related_po__supplier_id=supplier_id)
        if metric == "value":
            value_expr = ExpressionWrapper(
                F("quantity_change") * Coalesce(F("item__last_purchase_price"), 0),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        else:
            value_expr = F("quantity_change")
        rows = (
            qs.annotate(day=TruncDate("transaction_date"))
            .values("day")
            .annotate(
                total=Coalesce(
                    Sum(value_expr),
                    0,
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
            .order_by("day")
        )
        return JsonResponse(
            {
                "labels": [row["day"].strftime("%Y-%m-%d") for row in rows],
                "values": [float(row["total"] or 0) for row in rows],
            }
        )
    range_days = range_days_from_start_end(start, end)
    bundle = get_cached_dashboard_bundle(range_days, end)
    labels = bundle["trend_labels"]
    consumption = bundle["trend_consumption"]
    wastage = bundle["trend_wastage"]
    return JsonResponse(
        {"labels": labels, "consumption": consumption, "wastage": wastage}
    )
