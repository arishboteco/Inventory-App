from __future__ import annotations

from django.shortcuts import render

from ..forms.reorder_point_form import ReorderPointForm
from ..services import stock_service


def what_if_reorder(request):
    """Adjust reorder points and show projected stock levels."""

    form = ReorderPointForm(request.POST or None)
    projections = []
    if request.method == "POST" and form.is_valid():
        items = form.cleaned_data["items"]
        reorder_point = form.cleaned_data["reorder_point"]
        for item in items:
            item.reorder_point = reorder_point
            item.save(update_fields=["reorder_point"])
            history = stock_service.get_stock_history(item.pk)
            projections.append({"item": item, "history": history})
    return render(
        request,
        "inventory/what_if_reorder.html",
        {"form": form, "projections": projections},
    )
