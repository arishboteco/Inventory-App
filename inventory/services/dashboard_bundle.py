"""Cached dashboard KPIs + trend series for home page and related endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from inventory.services import dashboard_kpis as dkpis

BUNDLE_CACHE_PREFIX = "dashboard_bundle:v1"
BUNDLE_TTL_SECONDS = 90


def _bundle_cache_key(range_days: int, end: date) -> str:
    return f"{BUNDLE_CACHE_PREFIX}:{range_days}:{end.isoformat()}"


def range_days_from_start_end(start: date, end: date) -> int:
    return (end - start).days + 1


def compute_dashboard_bundle(start: date, end: date) -> Dict[str, Any]:
    """Run all dashboard KPI queries and daily trends (uncached).

    Each metric is isolated so one failing query does not blank the whole dashboard.
    """

    def _safe(call, default):
        try:
            return call()
        except Exception:
            return default

    try:
        trend_labels, trend_consumption, trend_wastage = dkpis.daily_trends(start, end)
    except Exception:
        trend_labels, trend_consumption, trend_wastage = [], [], []

    return {
        "opening_stock": _safe(lambda: dkpis.opening_stock_value(start, end), 0),
        "purchases": _safe(lambda: dkpis.purchases_total(start, end), 0),
        "closing_stock": _safe(lambda: dkpis.closing_stock_value(), 0),
        "consumption": _safe(lambda: dkpis.consumption_total(start, end), 0),
        "consumption_delta": _safe(lambda: dkpis.consumption_delta(start, end), None),
        "sales_revenue": _safe(lambda: dkpis.sales_revenue(start, end), 0),
        "actual_fc": _safe(lambda: dkpis.actual_food_cost_pct(start, end), None),
        "ideal_fc": _safe(lambda: dkpis.ideal_food_cost_pct(start, end), None),
        "wastage": _safe(lambda: dkpis.wastage_total(start, end), 0),
        "wastage_delta": _safe(lambda: dkpis.wastage_delta(start, end), None),
        "trend_labels": trend_labels,
        "trend_consumption": trend_consumption,
        "trend_wastage": trend_wastage,
    }


def get_cached_dashboard_bundle(
    range_days: int, end: date | None = None
) -> Dict[str, Any]:
    """Return KPIs + trends for [end - (range_days-1), end], cached."""
    end = end or timezone.now().date()
    start = end - timedelta(days=range_days - 1)
    if getattr(settings, "DISABLE_DASHBOARD_CACHE", False):
        return compute_dashboard_bundle(start, end)
    key = _bundle_cache_key(range_days, end)
    data = cache.get(key)
    if data is None:
        data = compute_dashboard_bundle(start, end)
        cache.set(key, data, BUNDLE_TTL_SECONDS)
    return data


def get_kpi_subset_for_partial(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Context for ``_kpi_cards.html`` (no trend arrays)."""
    return {k: bundle[k] for k in bundle if not k.startswith("trend_")}
