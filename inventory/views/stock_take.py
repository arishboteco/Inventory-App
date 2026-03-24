"""D4: Physical stock-take workflow views."""
from __future__ import annotations

import logging
from datetime import date

from django import forms
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..models import Department, Item, StockTake, StockTakeItem

logger = logging.getLogger(__name__)

SELECT_CLASS = (
    "block w-full px-3 py-2 border border-border rounded-md bg-surface text-bodyText "
    "focus:outline-none focus:ring-2 focus:ring-primary text-sm cursor-pointer"
)
INPUT_CLASS = (
    "block w-full px-3 py-2 border border-border rounded-md bg-surface text-bodyText "
    "focus:outline-none focus:ring-2 focus:ring-primary text-sm"
)


class StockTakeStartForm(forms.Form):
    date = forms.DateField(
        initial=date.today,
        widget=forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all().order_by("name"),
        required=False,
        empty_label="— All Departments —",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2, "placeholder": "Optional notes"}),
    )


def stock_take_list(request):
    stock_takes = StockTake.objects.select_related("department", "created_by").order_by("-date", "-created_at")
    return render(request, "inventory/stock_take_list.html", {
        "stock_takes": stock_takes,
        "list_url": "/",
        "list_title": "Dashboard",
        "current_title": "Stock Takes",
    })


def create_stock_take(request):
    if request.method == "POST":
        form = StockTakeStartForm(request.POST)
        if form.is_valid():
            dept = form.cleaned_data.get("department")
            with transaction.atomic():
                st = StockTake.objects.create(
                    date=form.cleaned_data["date"],
                    department=dept,
                    status="IN_PROGRESS",
                    notes=form.cleaned_data.get("notes") or "",
                    created_by=request.user,
                )
                items_qs = Item.objects.filter(is_active=True).order_by("name")
                if dept:
                    items_qs = items_qs.filter(departments=dept)
                StockTakeItem.objects.bulk_create([
                    StockTakeItem(
                        stock_take=st,
                        item=item,
                        system_qty=item.current_stock or 0,
                    )
                    for item in items_qs
                ])
            messages.success(request, f"Stock take #{st.pk} started.", extra_tags="toast")
            return redirect("stock_take_count", pk=st.pk)
    else:
        form = StockTakeStartForm()
    return render(request, "inventory/stock_take_start.html", {
        "form": form,
        "list_url": "/stock-takes/",
        "list_title": "Stock Takes",
        "current_title": "New Stock Take",
    })


def stock_take_count(request, pk: int):
    st = get_object_or_404(StockTake, pk=pk)
    if st.status == "COMPLETED":
        messages.info(request, "This stock take is already completed.", extra_tags="toast")
        return redirect("stock_take_review", pk=pk)

    items = list(st.items.select_related("item").order_by("item__name"))

    if request.method == "POST":
        with transaction.atomic():
            for sti in items:
                key = f"physical_{sti.pk}"
                raw = request.POST.get(key, "").strip()
                notes_key = f"notes_{sti.pk}"
                if raw:
                    try:
                        sti.physical_qty = float(raw)
                    except ValueError:
                        pass
                sti.notes = request.POST.get(notes_key, "") or ""
                sti.save(update_fields=["physical_qty", "notes"])
            st.status = "IN_PROGRESS"
            st.save(update_fields=["status"])
        messages.success(request, "Counts saved.", extra_tags="toast")
        return redirect("stock_take_review", pk=pk)

    return render(request, "inventory/stock_take_count.html", {
        "stock_take": st,
        "items": items,
        "list_url": "/stock-takes/",
        "list_title": "Stock Takes",
        "current_title": f"Count — Stock Take #{st.pk}",
    })


def stock_take_review(request, pk: int):
    st = get_object_or_404(StockTake, pk=pk)
    items = list(st.items.select_related("item").order_by("item__name"))

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "complete" and st.status != "COMPLETED":
            with transaction.atomic():
                st.status = "COMPLETED"
                st.completed_at = timezone.now()
                st.save(update_fields=["status", "completed_at"])
            messages.success(request, f"Stock take #{st.pk} completed.", extra_tags="toast")
            return redirect("stock_take_list")
        elif action == "discard":
            st.delete()
            messages.info(request, "Stock take discarded.", extra_tags="toast")
            return redirect("stock_take_list")

    counted = [i for i in items if i.physical_qty is not None]
    uncounted = len(items) - len(counted)
    total_variance = sum(
        (float(i.physical_qty or 0) - float(i.system_qty or 0))
        for i in counted
    )

    return render(request, "inventory/stock_take_review.html", {
        "stock_take": st,
        "items": items,
        "counted_count": len(counted),
        "uncounted_count": uncounted,
        "total_variance": total_variance,
        "list_url": "/stock-takes/",
        "list_title": "Stock Takes",
        "current_title": f"Review — Stock Take #{st.pk}",
    })
