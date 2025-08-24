from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render

from ..models import SaleTransaction, StockTransaction


def visualizations(request):
    metric = request.GET.get("metric", "sales")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    sales_qs = SaleTransaction.objects.all()
    stock_qs = StockTransaction.objects.all()

    if start_date:
        sales_qs = sales_qs.filter(sale_date__date__gte=start_date)
        stock_qs = stock_qs.filter(transaction_date__date__gte=start_date)
    if end_date:
        sales_qs = sales_qs.filter(sale_date__date__lte=end_date)
        stock_qs = stock_qs.filter(transaction_date__date__lte=end_date)

    sales_data = (
        sales_qs.annotate(date=TruncDate("sale_date"))
        .values("date")
        .annotate(total=Sum("quantity"))
        .order_by("date")
    )
    stock_data = (
        stock_qs.annotate(date=TruncDate("transaction_date"))
        .values("date")
        .annotate(total=Sum("quantity_change"))
        .order_by("date")
    )

    sales_map = {d["date"].isoformat(): float(d["total"]) for d in sales_data}
    stock_map = {d["date"].isoformat(): float(d["total"]) for d in stock_data}
    dates = sorted(set(sales_map) | set(stock_map))

    heatmap_z = [
        [sales_map.get(d, 0) for d in dates],
        [stock_map.get(d, 0) for d in dates],
    ]
    selected_map = sales_map if metric == "sales" else stock_map
    scatter_y = [selected_map.get(d, 0) for d in dates]

    context = {
        "metric": metric,
        "start_date": start_date,
        "end_date": end_date,
        "dates": dates,
        "heatmap_z": heatmap_z,
        "scatter_y": scatter_y,
    }
    return render(request, "inventory/visualizations.html", context)
