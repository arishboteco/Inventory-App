from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import DecimalField, F, Sum
from django.db.models.functions import Coalesce

from inventory.models import SavingsLedger, VendorItemPrice


@dataclass
class VendorBaseline:
    baseline_price: Decimal
    selected_price: Decimal
    cheapest_price: Decimal | None
    estimated_saving: Decimal
    estimated_loss: Decimal


def _to_decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _latest_vendor_price(item_id: int, vendor_id: int) -> Decimal | None:
    row = (
        VendorItemPrice.objects.filter(
            item_id=item_id,
            vendor_id=vendor_id,
            is_active=True,
        )
        .order_by("-effective_from", "-pk")
        .first()
    )
    return _to_decimal(row.price) if row else None


def _cheapest_vendor_price(item_id: int) -> Decimal | None:
    row = (
        VendorItemPrice.objects.filter(item_id=item_id, is_active=True)
        .order_by("price", "-effective_from", "-pk")
        .first()
    )
    return _to_decimal(row.price) if row else None


def baseline_for_po_line(
    *,
    item_id: int,
    selected_vendor_id: int,
    selected_unit_price,
    fallback_price,
) -> VendorBaseline:
    selected_price = _to_decimal(selected_unit_price)
    fallback = _to_decimal(fallback_price)
    vendor_latest = _latest_vendor_price(item_id, selected_vendor_id)
    cheapest = _cheapest_vendor_price(item_id)
    baseline = fallback
    if vendor_latest is not None:
        baseline = vendor_latest
    if cheapest is not None:
        baseline = min(baseline, cheapest)
    gap = baseline - selected_price
    estimated_saving = gap if gap > 0 else Decimal("0")
    estimated_loss = -gap if gap < 0 else Decimal("0")
    return VendorBaseline(
        baseline_price=baseline,
        selected_price=selected_price,
        cheapest_price=cheapest,
        estimated_saving=estimated_saving,
        estimated_loss=estimated_loss,
    )


def create_po_estimated_savings(
    *,
    po_id: int,
    po_date: date,
    supplier_id: int,
    po_lines: list[dict],
) -> None:
    entries: list[SavingsLedger] = []
    for line in po_lines:
        baseline = baseline_for_po_line(
            item_id=line["item_id"],
            selected_vendor_id=supplier_id,
            selected_unit_price=line["unit_price"],
            fallback_price=line.get("fallback_price"),
        )
        qty = _to_decimal(line["quantity_ordered"])
        entries.append(
            SavingsLedger(
                date=po_date,
                item_id=line["item_id"],
                saving_type=SavingsLedger.SavingType.VENDOR_SAVING,
                source_document_type="PO",
                source_document_id=str(po_id),
                baseline_price=baseline.baseline_price,
                selected_price=baseline.selected_price,
                quantity=qty,
                estimated_saving=baseline.estimated_saving * qty,
                lost_saving=baseline.estimated_loss * qty,
                status=SavingsLedger.Status.ESTIMATED,
                notes=("Auto-estimated on PO creation using vendor/item baseline."),
            )
        )
    if entries:
        SavingsLedger.objects.bulk_create(entries)


def apply_grn_realization(
    *,
    po_id: int,
    item_id: int,
    quantity_received,
    invoice_price,
) -> None:
    qty = _to_decimal(quantity_received)
    invoice = _to_decimal(invoice_price)
    estimates = SavingsLedger.objects.filter(
        source_document_type="PO",
        source_document_id=str(po_id),
        item_id=item_id,
        status=SavingsLedger.Status.ESTIMATED,
    ).order_by("pk")
    if not estimates.exists():
        return
    baseline = _to_decimal(estimates.first().baseline_price)
    diff = baseline - invoice
    confirmed = diff * qty if diff > 0 else Decimal("0")
    lost = -diff * qty if diff < 0 else Decimal("0")
    status = (
        SavingsLedger.Status.VERIFIED if confirmed > 0 else SavingsLedger.Status.LOST
    )
    estimates.update(
        invoice_price=invoice,
        confirmed_saving=Coalesce(F("confirmed_saving"), Decimal("0")) + confirmed,
        lost_saving=Coalesce(F("lost_saving"), Decimal("0")) + lost,
        status=status,
    )


def recovered_profit_for_month(*, year: int, month: int) -> Decimal:
    return SavingsLedger.objects.filter(
        date__year=year,
        date__month=month,
        status__in=[SavingsLedger.Status.CONFIRMED, SavingsLedger.Status.VERIFIED],
    ).aggregate(
        total=Coalesce(
            Sum("confirmed_saving"),
            Decimal("0"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )[
        "total"
    ] or Decimal(
        "0"
    )
