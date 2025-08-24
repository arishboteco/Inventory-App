from __future__ import annotations

from typing import Dict, List
from django.db.models import Sum
from django.db.models.functions import Abs, TruncDate
from statsmodels.tsa.holtwinters import SimpleExpSmoothing

from ..models import Item, StockTransaction


def forecast_item_demand(item: Item, periods: int = 7) -> List[float]:
    """Forecast future demand for an item using exponential smoothing.

    Args:
        item: Item to forecast.
        periods: Number of future periods (days) to predict.

    Returns:
        List of forecasted quantities for each future period. If fewer than two
        historical data points are available, returns zeros.
    """
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
    model = SimpleExpSmoothing(series).fit()
    forecast = model.forecast(periods)
    return [float(v) for v in forecast]


def train_models(periods: int = 7) -> Dict[int, List[float]]:
    """Train forecasting models for all items and return forecasts."""
    forecasts: Dict[int, List[float]] = {}
    for item in Item.objects.all():
        forecasts[item.pk] = forecast_item_demand(item, periods=periods)
    return forecasts


def abc_classification() -> Dict[int, str]:
    """Classify items into A/B/C categories based on usage quantity."""
    items = Item.objects.annotate(
        total=Abs(Sum("stocktransaction__quantity_change"))
    )
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
