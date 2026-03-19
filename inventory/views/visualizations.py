import json
import logging
from collections import defaultdict
from datetime import date, timedelta

from django.db import OperationalError, ProgrammingError
from django.shortcuts import render

from ..models import StockTransaction

logger = logging.getLogger(__name__)


def visualizations(request):
    metric = request.GET.get("metric", "receipts")
    start_raw = request.GET.get("start_date", "")
    end_raw = request.GET.get("end_date", "")

    # Default to last 30 days when no dates are provided
    end_date = date.fromisoformat(end_raw) if end_raw else date.today()
    start_date = (
        date.fromisoformat(start_raw) if start_raw else end_date - timedelta(days=30)
    )

    daily_receiving: defaultdict = defaultdict(float)
    daily_wastage: defaultdict = defaultdict(float)
    daily_adjust: defaultdict = defaultdict(float)

    try:
        qs = StockTransaction.objects.filter(
            transaction_date__date__gte=start_date,
            transaction_date__date__lte=end_date,
        ).values("transaction_date", "transaction_type", "quantity_change")

        for row in qs:
            if not row["transaction_date"]:
                continue
            d = row["transaction_date"].date().isoformat()
            val = float(row["quantity_change"] or 0)
            t = row["transaction_type"]
            if t == "RECEIVING":
                daily_receiving[d] += val
            elif t == "WASTAGE":
                daily_wastage[d] += abs(val)
            elif t == "ADJUSTMENT":
                daily_adjust[d] += val

    except (OperationalError, ProgrammingError) as exc:
        logger.warning("visualizations: DB query failed – %s", exc)

    all_dates = sorted(set(daily_receiving) | set(daily_wastage) | set(daily_adjust))

    # Heatmap: 3 rows — Receipts, Wastage, Adjustments
    heatmap_data = [
        [daily_receiving.get(d, 0) for d in all_dates],
        [daily_wastage.get(d, 0) for d in all_dates],
        [daily_adjust.get(d, 0) for d in all_dates],
    ]

    # Scatter Y varies by selected metric
    if metric == "wastage":
        scatter_y = [daily_wastage.get(d, 0) for d in all_dates]
    elif metric == "net":
        scatter_y = [
            daily_receiving.get(d, 0) - daily_wastage.get(d, 0) + daily_adjust.get(d, 0)
            for d in all_dates
        ]
    else:  # default: receipts
        scatter_y = [daily_receiving.get(d, 0) for d in all_dates]

    context = {
        "viz_metric": metric,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "viz_dates": json.dumps(all_dates),
        "viz_heatmap": json.dumps(heatmap_data),
        "viz_scatter_y": json.dumps(scatter_y),
        "has_data": len(all_dates) > 0,
        "metric": metric,
    }
    return render(request, "inventory/visualizations.html", context)
