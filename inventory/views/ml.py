import logging

from django.contrib import messages
from django.core.cache import cache
from django.db.models import Count
from django.shortcuts import redirect, render
from django.urls import reverse

from ..models import Item, StockTransaction
from ..services import ml

logger = logging.getLogger(__name__)

_FORECASTS_KEY = "ml_train_models"
_ABC_KEY = "ml_abc_classification"
_RUNNING_KEY = "ml_forecast_running"
_TIMESTAMP_KEY = "ml_last_run_ts"
_CACHE_TTL = 300  # 5 min
_MIN_DATA_POINTS = 2  # matches ml.forecast_item_demand threshold


def _compute_and_cache() -> tuple:
    """Queue both ML computations and fall back to synchronous computation."""
    from django.utils import timezone

    ml.queue_train_models(periods=1, cache_key=_FORECASTS_KEY, ttl=_CACHE_TTL)
    ml.queue_abc_classification(cache_key=_ABC_KEY, ttl=_CACHE_TTL)

    forecasts = cache.get(_FORECASTS_KEY)
    if forecasts is None:
        forecasts = ml.train_models(periods=1)
        cache.set(_FORECASTS_KEY, forecasts, _CACHE_TTL)

    classifications = cache.get(_ABC_KEY)
    if classifications is None:
        classifications = ml.abc_classification()
        cache.set(_ABC_KEY, classifications, _CACHE_TTL)

    cache.set(_TIMESTAMP_KEY, timezone.now(), _CACHE_TTL)
    return forecasts, classifications


def ml_dashboard(request):
    """Display forecasting and ABC classification results.

    GET:  serves cached results; computes synchronously on cache-miss so the
          page always shows real data without needing a background worker.
    POST: forces a fresh recompute, caches, then redirects.
    """
    if request.method == "POST":
        cache.set(_RUNNING_KEY, True, timeout=60)
        cache.delete(_FORECASTS_KEY)
        cache.delete(_ABC_KEY)
        try:
            _compute_and_cache()
        except Exception as exc:
            logger.exception("ML recompute failed")
            messages.error(request, f"Forecast failed: {exc}")
        else:
            messages.success(request, "Forecasts and ABC classifications updated.")
        finally:
            cache.delete(_RUNNING_KEY)
        return redirect("ml_dashboard")

    # ── GET ──────────────────────────────────────────────────────────────────
    forecasts = cache.get(_FORECASTS_KEY)
    classifications = cache.get(_ABC_KEY)

    if forecasts is None or classifications is None:
        try:
            forecasts, classifications = _compute_and_cache()
        except Exception as exc:
            logger.warning("ML compute on page load failed: %s", exc)
            forecasts = forecasts or {}
            classifications = classifications or {}

    last_run = cache.get(_TIMESTAMP_KEY)

    # Transaction count per active item — single query, used for has_data flag
    tx_counts = dict(
        StockTransaction.objects.filter(item__is_active=True)
        .values("item_id")
        .annotate(cnt=Count("transaction_id"))
        .values_list("item_id", "cnt")
    )

    items = (
        Item.objects.filter(is_active=True)
        .select_related("unit", "category")
        .order_by("name")
    )

    table_data = []
    for item in items:
        raw = forecasts.get(item.pk, [0.0])
        forecast_qty = float((raw[0] if isinstance(raw, list) and raw else raw) or 0)
        forecast_qty = max(0.0, forecast_qty)
        current_stock = float(item.current_stock or 0)
        days_cover = (
            round(current_stock / forecast_qty, 1) if forecast_qty > 0 else None
        )
        tx_count = tx_counts.get(item.pk, 0)

        table_data.append(
            {
                "item": item,
                "abc": classifications.get(item.pk, "C"),
                "forecast": forecast_qty,
                "days_cover": days_cover,
                "has_data": tx_count >= _MIN_DATA_POINTS,
                "tx_count": tx_count,
            }
        )

    # Sort: A → B → C; within each class, critical (low days_cover) first
    _abc_order = {"A": 0, "B": 1, "C": 2}
    table_data.sort(
        key=lambda r: (
            _abc_order.get(r["abc"], 2),
            r["days_cover"] if r["days_cover"] is not None else 9999,
            r["item"].name,
        )
    )

    # ABC distribution for page_meta
    abc_counts: dict = {"A": 0, "B": 0, "C": 0}
    for r in table_data:
        abc_counts[r["abc"]] = abc_counts.get(r["abc"], 0) + 1

    return render(
        request,
        "inventory/ml_dashboard.html",
        {
            "table_data": table_data,
            "abc_counts": abc_counts,
            "last_run": last_run,
            "task_running": cache.get(_RUNNING_KEY, False),
            "list_url": reverse("root"),
            "list_title": "Dashboard",
            "current_title": "ML Planner",
        },
    )
