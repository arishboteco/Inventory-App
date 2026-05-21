from __future__ import annotations

from datetime import date, timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from inventory.models import ChefBulletin
from inventory.services.chef_bulletins_service import (
    apply_chef_decision,
    refresh_chef_bulletins,
)


def _parse_date(raw: str, fallback: date) -> date:
    value = (raw or "").strip()
    if not value:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError:
        return fallback


def chef_bulletins_list(request):
    today = timezone.localdate()
    default_start = today - timedelta(days=29)
    start_date = _parse_date(request.GET.get("start_date", ""), default_start)
    end_date = _parse_date(request.GET.get("end_date", ""), today)
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    alert_type = (request.GET.get("alert_type") or "").strip()
    risk = (request.GET.get("risk") or "").strip()
    state = (request.GET.get("state") or "open").strip().lower()

    refresh_chef_bulletins(start_date, end_date)
    qs = ChefBulletin.objects.select_related("recipe", "decided_by").filter(
        period_start=start_date,
        period_end=end_date,
    )
    if alert_type:
        qs = qs.filter(alert_type=alert_type)
    if risk:
        qs = qs.filter(risk_level=risk)
    if state == "open":
        qs = qs.filter(is_open=True)
    elif state == "closed":
        qs = qs.filter(is_open=False)

    qs = qs.order_by("-is_open", "-expected_saving", "-updated_at")
    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get("page"))

    summary = {
        "open_count": qs.filter(is_open=True).count(),
        "closed_count": qs.filter(is_open=False).count(),
        "high_risk_count": qs.filter(risk_level=ChefBulletin.RiskLevel.HIGH).count(),
    }

    return render(
        request,
        "inventory/chef_bulletins/list.html",
        {
            "page_obj": page_obj,
            "summary": summary,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "alert_type": alert_type,
            "risk": risk,
            "state": state,
            "alert_type_choices": ChefBulletin.AlertType.choices,
            "risk_choices": ChefBulletin.RiskLevel.choices,
        },
    )


def chef_bulletin_detail(request, bulletin_id: int):
    bulletin = get_object_or_404(
        ChefBulletin.objects.select_related("recipe", "decided_by"),
        pk=bulletin_id,
    )
    return render(
        request,
        "inventory/chef_bulletins/detail.html",
        {
            "bulletin": bulletin,
            "decision_choices": ChefBulletin.ChefDecision.choices,
        },
    )


@require_POST
def chef_bulletin_decision(request, bulletin_id: int):
    bulletin = get_object_or_404(ChefBulletin, pk=bulletin_id)
    decision = request.POST.get("decision", "")
    notes = request.POST.get("decision_notes", "")
    try:
        result = apply_chef_decision(
            bulletin=bulletin,
            decision=decision,
            user=request.user,
            notes=notes,
        )
    except ValueError as exc:
        messages.error(request, str(exc), extra_tags="toast")
        return redirect("chef_bulletin_detail", bulletin_id=bulletin_id)

    if result.trial_version and result.trial_version.trial_recipe:
        messages.success(
            request,
            (
                f"Decision saved. Trial recipe created: "
                f"{result.trial_version.trial_recipe.name}"
            ),
            extra_tags="toast",
        )
    else:
        messages.success(request, "Chef decision saved.", extra_tags="toast")
    return redirect("chef_bulletin_detail", bulletin_id=bulletin_id)
