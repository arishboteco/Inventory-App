from __future__ import annotations

import logging
from typing import Dict, List, Optional

from django.core.cache import cache
from django.db.models import Sum
from django.db.models.functions import Abs, TruncDate
from django_q.tasks import async_task
from statsmodels.tsa.holtwinters import SimpleExpSmoothing

from ..models import Item, StockTransaction

logger = logging.getLogger(__name__)


def forecast_item_demand(
    item: Optional[Item] = None,
    *,
    periods: int = 7,
    series: Optional[List[float]] = None,
) -> List[float]:
    """Forecast future demand for an item using exponential smoothing.

    Either ``item`` or ``series`` must be provided. When ``series`` is supplied
    the database is not queried, allowing callers to batch-load time series data
    and avoid per-item queries.

    Args:
        item: Item to forecast. Required if ``series`` is not provided.
        periods: Number of future periods (days) to predict.
        series: Precomputed historical demand values.

    Returns:
        List of forecasted quantities for each future period. If fewer than two
        historical data points are available, returns zeros.
    """
    if series is None:
        if item is None:
            raise ValueError("Either item or series must be provided")
        qs = (
            StockTransaction.objects.filter(item=item)
            .annotate(day=TruncDate("transaction_date"))
            .values("day")
            .annotate(total=Sum("quantity_change"))
            .order_by("day")
        )
        series = [float(row["total"]) for row in qs]

    if len(series) < 2:
        return [0.0 for _ in range(periods)]
    try:
        model = SimpleExpSmoothing(series).fit()
        forecast = model.forecast(periods)
    except ValueError:
        logger.exception(
            "Failed to forecast demand for item %s", getattr(item, "pk", "<series>")
        )
        return [0.0 for _ in range(periods)]
    return [float(v) for v in forecast]


def train_models(periods: int = 7) -> Dict[int, List[float]]:
    """Train forecasting models for all items and return forecasts.

    To avoid per-item database queries the required stock data for all items is
    fetched in a single aggregated query and the precomputed series are passed to
    :func:`forecast_item_demand`.
    """
    data = (
        StockTransaction.objects.annotate(day=TruncDate("transaction_date"))
        .values("item_id", "day")
        .annotate(total=Sum("quantity_change"))
        .order_by("item_id", "day")
    )

    series_by_item: Dict[int, List[float]] = {}
    for row in data:
        series_by_item.setdefault(row["item_id"], []).append(float(row["total"]))

    forecasts: Dict[int, List[float]] = {}
    for item_id in Item.objects.values_list("pk", flat=True):
        series = series_by_item.get(item_id, [])
        forecasts[item_id] = forecast_item_demand(
            periods=periods, series=series if series else [0.0]
        )

    return forecasts


def train_models_task(periods: int, cache_key: str, ttl: int) -> bool:
    """Train models and store results in cache.

    Returns ``True`` on success and ``False`` if an exception is raised.
    """
    try:
        cache.set(cache_key, train_models(periods), ttl)
        return True
    except Exception:  # pragma: no cover - defensive catch-all
        logger.exception("Failed to train forecasting models")
        return False


def queue_train_models(
    periods: int = 7,
    *,
    cache_key: str = "ml_train_models",
    ttl: int = 300,
    sync: bool = False,
) -> str:
    """Queue training task and store results in cache when complete.

    Args:
        periods: Number of future periods (days) to predict.
        cache_key: Cache key to store forecasts.
        ttl: Cache time-to-live in seconds.
        sync: If ``True`` the task runs synchronously (used in tests).

    Returns:
        The ID of the queued task.
    """

    return async_task(train_models_task, periods, cache_key, ttl, sync=sync)


def abc_classification() -> Dict[int, str]:
    """Classify items into A/B/C categories based on usage quantity."""
    items = Item.objects.annotate(total=Abs(Sum("stocktransaction__quantity_change")))
    totals = [(item, float(item.total or 0)) for item in items]
    totals.sort(key=lambda x: x[1], reverse=True)
    overall = sum(v for _, v in totals)
    cumulative = 0.0
    classifications: Dict[int, str] = {}
    for item, value in totals:
        cumulative += value
        pct = cumulative / overall if overall else 0
        if pct <= 0.8:
            cls = "A"
        elif pct <= 0.95:
            cls = "B"
        else:
            cls = "C"
        classifications[item.pk] = cls
    return classifications
