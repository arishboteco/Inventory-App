import json
import logging
from datetime import timedelta

from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from inventory.models import Indent, Item, PurchaseOrder
from inventory.models.enums import PurchaseOrderStatus
from inventory.models.stock_take import StockTake
from inventory.services import dashboard_kpis as dkpis
from inventory.services import kpis
from inventory.services.stock_utils import get_low_stock_items

logger = logging.getLogger(__name__)


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


def _build_alerts():
    """Build a list of alert dicts for the dashboard attention panel."""
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
        actual_fc = dkpis.actual_food_cost_pct(
            timezone.now().date() - timedelta(days=29),
            timezone.now().date(),
        )
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

        try:
            opening = dkpis.opening_stock_value(start, end)
        except Exception:
            opening = 0
        try:
            closing = dkpis.closing_stock_value()
        except Exception:
            closing = 0
        try:
            purchases = dkpis.purchases_total(start, end)
        except Exception:
            purchases = 0
        try:
            consumption = dkpis.consumption_total(start, end)
        except Exception:
            consumption = 0
        try:
            cons_delta = dkpis.consumption_delta(start, end)
        except Exception:
            cons_delta = None
        try:
            revenue = dkpis.sales_revenue(start, end)
        except Exception:
            revenue = 0
        try:
            actual_fc = dkpis.actual_food_cost_pct(start, end)
        except Exception:
            actual_fc = None
        try:
            ideal_fc = dkpis.ideal_food_cost_pct(start, end)
        except Exception:
            ideal_fc = None
        try:
            wastage = dkpis.wastage_total(start, end)
        except Exception:
            wastage = 0
        try:
            waste_delta = dkpis.wastage_delta(start, end)
        except Exception:
            waste_delta = None
        try:
            trend_labels, trend_consumption, trend_wastage = dkpis.daily_trends(
                start, end
            )
        except Exception:
            trend_labels, trend_consumption, trend_wastage = [], [], []

        active_items = Item.objects.filter(is_active=True).count()
        low_stock_count = kpis.low_stock_count()
        low_stock_pct = (
            round(low_stock_count / active_items * 100, 1) if active_items else 0
        )
        try:
            stock_value = float(dkpis.closing_stock_value())
        except Exception:
            stock_value = 0
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
            "alerts": _build_alerts(),
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
    """HTMX endpoint returning KPI card values."""
    end = timezone.now().date()
    range_days = int(request.GET.get("range", "30"))
    start = end - timedelta(days=range_days - 1)
    data = {
        "opening_stock": dkpis.opening_stock_value(start, end),
        "purchases": dkpis.purchases_total(start, end),
        "closing_stock": dkpis.closing_stock_value(),
        "consumption": dkpis.consumption_total(start, end),
        "consumption_delta": dkpis.consumption_delta(start, end),
        "sales_revenue": dkpis.sales_revenue(start, end),
        "actual_fc": dkpis.actual_food_cost_pct(start, end),
        "ideal_fc": dkpis.ideal_food_cost_pct(start, end),
        "wastage": dkpis.wastage_total(start, end),
        "wastage_delta": dkpis.wastage_delta(start, end),
    }
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
    labels, consumption, wastage = dkpis.daily_trends(start, end)
    return JsonResponse(
        {"labels": labels, "consumption": consumption, "wastage": wastage}
    )
