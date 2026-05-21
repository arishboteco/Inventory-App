from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone

from inventory.models import ChefBulletin, RecoveryAction, SavingsLedger
from inventory.services.chef_bulletins_service import refresh_chef_bulletins
from inventory.services.variance_service import build_variance_report

ZERO = Decimal("0.00")
OPEN_STATUSES = {
    RecoveryAction.Status.SUGGESTED,
    RecoveryAction.Status.ASSIGNED,
    RecoveryAction.Status.IN_PROGRESS,
    RecoveryAction.Status.IMPLEMENTED,
}
IN_PROGRESS_STATUSES = {
    RecoveryAction.Status.ASSIGNED,
    RecoveryAction.Status.IN_PROGRESS,
    RecoveryAction.Status.IMPLEMENTED,
}

ALERT_TO_LEAKAGE = {
    ChefBulletin.AlertType.FOOD_COST_ABOVE_TARGET: RecoveryAction.LeakageType.FOOD_COST_GAP,
    ChefBulletin.AlertType.INGREDIENT_PRICE_INCREASED: RecoveryAction.LeakageType.VENDOR_PRICE,
    ChefBulletin.AlertType.RECIPE_COST_CHANGED: RecoveryAction.LeakageType.RECIPE_OPTIMISATION,
    ChefBulletin.AlertType.HIGH_SALES_LOW_MARGIN: RecoveryAction.LeakageType.MENU_PRICE_CORRECTION,
    ChefBulletin.AlertType.ACTUAL_USAGE_ABOVE_IDEAL: RecoveryAction.LeakageType.VARIANCE_REDUCTION,
}

LEAKAGE_TO_SAVING = {
    RecoveryAction.LeakageType.FOOD_COST_GAP: SavingsLedger.SavingType.RECIPE_OPTIMISATION,
    RecoveryAction.LeakageType.VENDOR_PRICE: SavingsLedger.SavingType.VENDOR_SAVING,
    RecoveryAction.LeakageType.INVOICE_MISMATCH: SavingsLedger.SavingType.INVOICE_MISMATCH_CAUGHT,
    RecoveryAction.LeakageType.RECIPE_OPTIMISATION: SavingsLedger.SavingType.RECIPE_OPTIMISATION,
    RecoveryAction.LeakageType.WASTE_REDUCTION: SavingsLedger.SavingType.WASTE_REDUCTION,
    RecoveryAction.LeakageType.VARIANCE_REDUCTION: SavingsLedger.SavingType.VARIANCE_REDUCTION,
    RecoveryAction.LeakageType.MENU_PRICE_CORRECTION: SavingsLedger.SavingType.MENU_PRICE_CORRECTION,
}

CHEF_LEAKAGE_TYPES = {
    RecoveryAction.LeakageType.FOOD_COST_GAP,
    RecoveryAction.LeakageType.RECIPE_OPTIMISATION,
    RecoveryAction.LeakageType.WASTE_REDUCTION,
    RecoveryAction.LeakageType.VARIANCE_REDUCTION,
    RecoveryAction.LeakageType.MENU_PRICE_CORRECTION,
}
PURCHASE_LEAKAGE_TYPES = {
    RecoveryAction.LeakageType.VENDOR_PRICE,
    RecoveryAction.LeakageType.INVOICE_MISMATCH,
}


def _as_decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return ZERO
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _money_sum(queryset, field_name: str) -> Decimal:
    value = queryset.aggregate(
        total=Coalesce(
            Sum(field_name),
            Decimal("0"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["total"]
    return _as_decimal(value)


def _default_window(
    start_date: date | None,
    end_date: date | None,
) -> tuple[date, date]:
    end = end_date or timezone.localdate()
    start = start_date or (end - timedelta(days=29))
    if start > end:
        return end, start
    return start, end


def _action_title_for_bulletin(bulletin: ChefBulletin) -> str:
    return f"Recover {bulletin.recipe.name}: {bulletin.get_alert_type_display()}"


def _create_suggestions_from_bulletins(
    *,
    start_date: date,
    end_date: date,
) -> int:
    created = 0
    bulletins = ChefBulletin.objects.select_related("recipe").filter(
        is_open=True,
        period_start=start_date,
        period_end=end_date,
    )
    for bulletin in bulletins:
        exists = RecoveryAction.objects.filter(
            linked_chef_bulletin=bulletin,
            status__in=OPEN_STATUSES,
        ).exists()
        if exists:
            continue
        RecoveryAction.objects.create(
            title=_action_title_for_bulletin(bulletin),
            leakage_type=ALERT_TO_LEAKAGE.get(
                bulletin.alert_type,
                RecoveryAction.LeakageType.RECIPE_OPTIMISATION,
            ),
            expected_saving=_as_decimal(bulletin.expected_saving),
            due_date=end_date + timedelta(days=7),
            linked_chef_bulletin=bulletin,
            notes=bulletin.suggested_change or "",
        )
        created += 1
    return created


def _create_suggestions_from_variance(
    *,
    start_date: date,
    end_date: date,
) -> int:
    created = 0
    report = build_variance_report(start_date, end_date)
    for row in report["rows"]:
        unexplained = _as_decimal(row.unexplained_variance_value)
        if unexplained <= ZERO:
            continue
        exists = RecoveryAction.objects.filter(
            leakage_type=RecoveryAction.LeakageType.VARIANCE_REDUCTION,
            linked_item=row.item,
            linked_chef_bulletin__isnull=True,
            status__in=OPEN_STATUSES,
        ).exists()
        if exists:
            continue
        RecoveryAction.objects.create(
            title=f"Reduce unexplained variance: {row.item.name}",
            leakage_type=RecoveryAction.LeakageType.VARIANCE_REDUCTION,
            expected_saving=unexplained,
            due_date=end_date + timedelta(days=7),
            linked_item=row.item,
            notes=row.recommended_action,
        )
        created += 1
    return created


def refresh_recovery_actions(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, int]:
    start_date, end_date = _default_window(start_date, end_date)
    refresh_chef_bulletins(start_date, end_date)
    from_bulletins = _create_suggestions_from_bulletins(
        start_date=start_date,
        end_date=end_date,
    )
    from_variance = _create_suggestions_from_variance(
        start_date=start_date,
        end_date=end_date,
    )
    return {
        "created_from_bulletins": from_bulletins,
        "created_from_variance": from_variance,
    }


def summarize_recovery_actions() -> dict[str, Decimal]:
    qs = RecoveryAction.objects.all()
    open_opportunity = _money_sum(
        qs.filter(status__in=OPEN_STATUSES),
        "expected_saving",
    )
    expected_recovery = _money_sum(
        qs.filter(status__in=IN_PROGRESS_STATUSES),
        "expected_saving",
    )
    verified_recovered_profit = _money_sum(
        qs.filter(status=RecoveryAction.Status.VERIFIED),
        "verified_saving",
    )
    return {
        "open_opportunity": open_opportunity,
        "expected_recovery": expected_recovery,
        "verified_recovered_profit": verified_recovered_profit,
    }


def weekly_action_plan_from_actions(limit: int = 3) -> list[dict[str, Any]]:
    actions = (
        RecoveryAction.objects.select_related("assigned_to")
        .filter(status__in=OPEN_STATUSES)
        .order_by("due_date", "-expected_saving", "-created_at")[:limit]
    )
    plan: list[dict[str, Any]] = []
    for action in actions:
        assigned = action.assigned_to.username if action.assigned_to else "Unassigned"
        due = action.due_date.strftime("%d %b") if action.due_date else "No due date"
        plan.append(
            {
                "title": action.title,
                "detail": f"{action.get_status_display()} | {assigned} | Due {due}",
                "url": reverse("recovery_action_detail", kwargs={"action_id": action.pk}),
            }
        )
    return plan


def apply_recovery_action_status(
    *,
    action: RecoveryAction,
    status: str,
    notes: str = "",
    verified_saving: Decimal | None = None,
    implemented_date: date | None = None,
) -> SavingsLedger | None:
    valid_statuses = {choice[0] for choice in RecoveryAction.Status.choices}
    if status not in valid_statuses:
        raise ValueError("Invalid recovery action status.")

    action.status = status
    if notes:
        action.notes = notes

    if status == RecoveryAction.Status.IMPLEMENTED:
        action.implemented_date = implemented_date or timezone.localdate()
        action.save()
        return None

    if status != RecoveryAction.Status.VERIFIED:
        action.save()
        return None

    value = _as_decimal(verified_saving or 0)
    if value <= ZERO:
        raise ValueError("Verified saving must be greater than zero.")

    action.verified_saving = value
    action.implemented_date = implemented_date or action.implemented_date or timezone.localdate()
    action.save()

    ledger_defaults = {
        "saving_type": LEAKAGE_TO_SAVING.get(
            action.leakage_type,
            SavingsLedger.SavingType.RECIPE_OPTIMISATION,
        ),
        "status": SavingsLedger.Status.VERIFIED,
        "item": action.linked_item,
        "estimated_saving": _as_decimal(action.expected_saving),
        "confirmed_saving": value,
        "lost_saving": ZERO,
        "notes": f"Recovery action #{action.pk}: {action.title}",
    }
    ledger, _ = SavingsLedger.objects.update_or_create(
        source_document_type="RecoveryAction",
        source_document_id=str(action.pk),
        defaults={
            "date": action.implemented_date or timezone.localdate(),
            "baseline_price": ZERO,
            "selected_price": ZERO,
            "invoice_price": ZERO,
            "quantity": Decimal("0.000"),
            **ledger_defaults,
        },
    )
    action.linked_savings_entries.add(ledger)
    return ledger
