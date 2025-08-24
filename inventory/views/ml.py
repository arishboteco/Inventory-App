from django.shortcuts import render

from ..models import Item
from ..services import ml


def ml_dashboard(request):
    """Display forecasting and ABC classification results."""
    forecasts = ml.train_models(periods=1)
    classifications = ml.abc_classification()
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
