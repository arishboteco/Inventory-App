from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from inventory_app.navigation import ROLE_HEAD_CHEF, ROLE_PURCHASE, get_primary_role

from ..forms.recovery_forms import (
    RecoveryActionForm,
    RecoveryActionStatusForm,
    SavingsLedgerForm,
    VendorItemPriceForm,
)
from ..models import RecoveryAction, SavingsLedger, VendorItemPrice
from ..services.recovery_actions_service import (
    CHEF_LEAKAGE_TYPES,
    PURCHASE_LEAKAGE_TYPES,
    apply_recovery_action_status,
    refresh_recovery_actions,
    summarize_recovery_actions,
)


def _money_total(field_name: str):
    return Coalesce(Sum(field_name), Decimal("0.00"))


def _parse_date(raw_value: str):
    value = (raw_value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


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


def _role_scoped_actions_queryset(request, qs):
    role = get_primary_role(getattr(request, "user", None))
    if role == ROLE_PURCHASE:
        return qs.filter(leakage_type__in=PURCHASE_LEAKAGE_TYPES)
    if role == ROLE_HEAD_CHEF:
        return qs.filter(leakage_type__in=CHEF_LEAKAGE_TYPES)
    return qs


def recovery_actions_list(request):
    start_date = _parse_date(request.GET.get("start_date", "")) or (
        timezone.localdate() - timedelta(days=29)
    )
    end_date = _parse_date(request.GET.get("end_date", "")) or timezone.localdate()
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    refresh_recovery_actions(start_date, end_date)

    status = (request.GET.get("status") or "").strip()
    leakage_type = (request.GET.get("leakage_type") or "").strip()
    assigned_to = (request.GET.get("assigned_to") or "").strip()

    qs = RecoveryAction.objects.select_related(
        "assigned_to",
        "linked_item",
        "linked_chef_bulletin__recipe",
    ).prefetch_related("linked_savings_entries")
    qs = _role_scoped_actions_queryset(request, qs)

    if status:
        qs = qs.filter(status=status)
    if leakage_type:
        qs = qs.filter(leakage_type=leakage_type)
    if assigned_to.isdigit():
        qs = qs.filter(assigned_to_id=int(assigned_to))

    if request.method == "POST":
        form = RecoveryActionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Recovery action saved", extra_tags="toast")
            return redirect("recovery_actions_list")
    else:
        form = RecoveryActionForm()

    paginator = Paginator(qs.order_by("due_date", "-expected_saving", "-created_at"), 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    summary = summarize_recovery_actions()

    return render(
        request,
        "inventory/recovery/recovery_actions_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "summary": summary,
            "status": status,
            "leakage_type": leakage_type,
            "assigned_to": assigned_to,
            "status_choices": RecoveryAction.Status.choices,
            "leakage_type_choices": RecoveryAction.LeakageType.choices,
            "assigned_user_choices": get_user_model()
            .objects.filter(is_active=True)
            .order_by("username"),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    )


def recovery_action_detail(request, action_id: int):
    action = get_object_or_404(
        RecoveryAction.objects.select_related(
            "assigned_to",
            "linked_item",
            "linked_chef_bulletin__recipe",
        ).prefetch_related("linked_savings_entries"),
        pk=action_id,
    )
    status_form = RecoveryActionStatusForm(
        initial={
            "status": action.status,
            "verified_saving": action.verified_saving,
            "implemented_date": action.implemented_date,
            "notes": action.notes,
        }
    )
    return render(
        request,
        "inventory/recovery/recovery_action_detail.html",
        {
            "action": action,
            "status_form": status_form,
        },
    )


@require_POST
def recovery_action_status(request, action_id: int):
    action = get_object_or_404(RecoveryAction, pk=action_id)
    form = RecoveryActionStatusForm(request.POST)
    if not form.is_valid():
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error, extra_tags="toast")
        return redirect("recovery_action_detail", action_id=action_id)

    cleaned = form.cleaned_data
    try:
        ledger = apply_recovery_action_status(
            action=action,
            status=cleaned["status"],
            notes=cleaned.get("notes") or "",
            verified_saving=cleaned.get("verified_saving"),
            implemented_date=cleaned.get("implemented_date"),
        )
    except ValueError as exc:
        messages.error(request, str(exc), extra_tags="toast")
        return redirect("recovery_action_detail", action_id=action_id)

    if ledger is not None:
        messages.success(
            request,
            "Action verified and linked to savings ledger.",
            extra_tags="toast",
        )
    else:
        messages.success(request, "Action status updated.", extra_tags="toast")
    return redirect("recovery_action_detail", action_id=action_id)
