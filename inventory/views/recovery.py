from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render
from django.utils import timezone

from ..forms.recovery_forms import SavingsLedgerForm, VendorItemPriceForm
from ..models import SavingsLedger, VendorItemPrice


def _money_total(field_name: str):
    return Coalesce(Sum(field_name), Decimal("0.00"))


def savings_ledger_list(request):
    status = (request.GET.get("status") or "").strip()
    saving_type = (request.GET.get("saving_type") or "").strip()

    qs = SavingsLedger.objects.select_related("item").all()
    if status:
        qs = qs.filter(status=status)
    if saving_type:
        qs = qs.filter(saving_type=saving_type)

    if request.method == "POST":
        form = SavingsLedgerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Savings ledger entry saved", extra_tags="toast")
            return redirect("savings_ledger_list")
    else:
        form = SavingsLedgerForm(initial={"date": timezone.localdate()})

    summary = qs.aggregate(
        estimated_total=_money_total("estimated_saving"),
        confirmed_total=_money_total("confirmed_saving"),
        lost_total=_money_total("lost_saving"),
    )
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "inventory/recovery/savings_ledger_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "status": status,
            "saving_type": saving_type,
            "status_choices": SavingsLedger.Status.choices,
            "saving_type_choices": SavingsLedger.SavingType.choices,
            "summary": summary,
        },
    )


def vendor_prices_list(request):
    vendor = (request.GET.get("vendor") or "").strip()
    item = (request.GET.get("item") or "").strip()
    active = (request.GET.get("active") or "").strip()

    qs = VendorItemPrice.objects.select_related("vendor", "item", "unit").all()
    if vendor:
        qs = qs.filter(vendor__name__icontains=vendor)
    if item:
        qs = qs.filter(item__name__icontains=item)
    if active in {"1", "0"}:
        qs = qs.filter(is_active=(active == "1"))

    if request.method == "POST":
        form = VendorItemPriceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Vendor price saved", extra_tags="toast")
            return redirect("vendor_prices_list")
    else:
        form = VendorItemPriceForm(initial={"effective_from": timezone.localdate()})

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "inventory/recovery/vendor_prices_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "vendor": vendor,
            "item": item,
            "active": active,
            "active_count": VendorItemPrice.objects.filter(is_active=True).count(),
            "inactive_count": VendorItemPrice.objects.filter(is_active=False).count(),
        },
    )
