from django.core.cache import cache
from django.shortcuts import render

from ..models import Item
from ..services import ml


def ml_dashboard(request):
    """Display forecasting and ABC classification results.

    The results of :func:`ml.train_models` and :func:`ml.abc_classification` are
    cached for a short period to avoid repeatedly running relatively expensive
    operations on every request. Results are recomputed only when the cache is
    empty or expires.
    """
    ttl = 300  # seconds

    forecasts = cache.get("ml_train_models")
    if forecasts is None:
        # Training can be expensive. Trigger it in the background and use any
        # cached results available. The background task populates the cache when
        # finished so subsequent requests receive data without blocking.
        ml.queue_train_models(periods=1, ttl=ttl)
        forecasts = {}

    classifications = cache.get("ml_abc_classification")
    if classifications is None:
        classifications = ml.abc_classification()
        cache.set("ml_abc_classification", classifications, ttl)

    results = []
    for item in Item.objects.all():
        forecast = forecasts.get(item.pk, [0.0])[0] if forecasts.get(item.pk) else 0.0
        results.append(
            {
                "item": item,
                "forecast": forecast,
                "classification": classifications.get(item.pk, "C"),
            }
        )
    return render(request, "inventory/ml_dashboard.html", {"results": results})
