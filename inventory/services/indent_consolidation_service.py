import logging
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from inventory.models import Indent, IndentItem, Item, PurchaseOrder
from . import purchase_order_service

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationResult:
    created_po_ids: List[int]
    skipped_items: int
    total_items: int


def _pending_qty(ii: IndentItem) -> Decimal:
    req = Decimal(str(ii.requested_qty or 0))
    iss = Decimal(str(ii.issued_qty or 0))
    pending = req - iss
    return pending if pending > 0 else Decimal("0")


def consolidate_approved_indents(indent_ids: Iterable[int]) -> ConsolidationResult:
    """Group approved indent items by preferred supplier and create POs.

    Constraints: no schema changes, so we do not create explicit linkage rows.
    We annotate `IndentItem.notes` with simple references for traceability.
    """

    indent_ids = list(indent_ids or [])
    if not indent_ids:
        return ConsolidationResult(created_po_ids=[], skipped_items=0, total_items=0)

    indents = (
        Indent.objects.filter(indent_id__in=indent_ids, status__in=["APPROVED", "PROCESSING"])  # type: ignore
        .only("indent_id", "status", "date_required")
    )
    items = (
        IndentItem.objects.select_related("item")
        .filter(indent_id__in=[i.pk for i in indents])
        .only("indent_id", "indent_item_id", "item_id", "requested_qty", "issued_qty", "item_status", "notes")
    )
    # Build supplier -> item -> total pending
    supplier_items: Dict[int, Dict[int, Dict[str, Decimal]]] = defaultdict(dict)
    total = 0
    skipped = 0
    for ii in items:
        pending = _pending_qty(ii)
        if not pending:
            continue
        total += 1
        itm: Item = ii.item  # type: ignore
        supplier_id = getattr(itm, "preferred_supplier_id", None)
        if not supplier_id:
            skipped += 1
            continue
        entry = supplier_items.setdefault(supplier_id, {}).setdefault(itm.pk, {"qty": Decimal("0"), "price": Decimal(str(itm.last_purchase_price or 0))})
        entry["qty"] += pending

    created_po_ids: List[int] = []
    order_date = timezone.now().date()

    # Create POs per supplier
    for supplier_id, item_map in supplier_items.items():
        items_data = [
            {
                "item_id": item_id,
                "quantity_ordered": data["qty"],
                "unit_price": data["price"],
            }
            for item_id, data in item_map.items()
            if data["qty"] > 0
        ]
        if not items_data:
            continue
        po_id = purchase_order_service.create_po(
            {"supplier_id": supplier_id, "order_date": order_date, "status": "DRAFT"},
            items_data,
        )
        created_po_ids.append(po_id)

    # Mark consolidated indents as PROCESSING if any PO created
    if created_po_ids:
        with transaction.atomic():
            Indent.objects.filter(indent_id__in=[i.pk for i in indents], status="APPROVED").update(status="PROCESSING")
            # Best-effort traceability note on items
            note_suffix = ", ".join([f"PO#{pid}" for pid in created_po_ids])
            try:
                IndentItem.objects.filter(indent_id__in=[i.pk for i in indents]).update(
                    notes=(
                        ("" if IndentItem.notes.field.default is None else str(IndentItem.notes.field.default))
                    )
                )
            except Exception:
                # Fallback: append per-row to avoid clobbering existing notes
                for ii in items:
                    try:
                        ii.notes = ((ii.notes or "").strip() + (f" | {note_suffix}" if note_suffix else "")).strip()
                        ii.save(update_fields=["notes"])
                    except Exception:
                        logger.warning("Failed to annotate IndentItem %s with PO refs", ii.pk)

    return ConsolidationResult(created_po_ids=created_po_ids, skipped_items=skipped, total_items=total)


def apply_receipts_to_indents(receipts: List[Dict[str, Decimal]]) -> None:
    """Allocate received quantities to outstanding indent items by item.

    Strategy: for each (item_id, qty_received), allocate to IndentItems
    with pending > 0 ordered by date_required (asc), then created_at.
    When an indent's all items are fully allocated, mark it COMPLETED.
    """
    if not receipts:
        return
    by_item: Dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for r in receipts:
        try:
            by_item[int(r["item_id"])] += Decimal(str(r["quantity_received"]))
        except Exception:
            continue
    if not by_item:
        return
    with transaction.atomic():
        for item_id, qty in by_item.items():
            if qty <= 0:
                continue
            # Select outstanding indent items for this item
            outstanding = (
                IndentItem.objects.select_related("indent")
                .filter(item_id=item_id, indent__status__in=["APPROVED", "PROCESSING"])  # type: ignore
                .order_by("indent__date_required", "indent__created_at", "indent_item_id")
            )
            for ii in outstanding:
                if qty <= 0:
                    break
                pending = _pending_qty(ii)
                if pending <= 0:
                    continue
                alloc = qty if qty <= pending else pending
                ii.issued_qty = (Decimal(str(ii.issued_qty or 0)) + alloc)
                # If fully allocated, mark item as ISSUED
                try:
                    from inventory.models.enums import ItemStatus

                    if ii.issued_qty >= Decimal(str(ii.requested_qty or 0)):
                        ii.item_status = ItemStatus.ISSUED
                except Exception:
                    pass
                ii.save(update_fields=["issued_qty", "item_status"])
                qty -= alloc
            # Roll up indent statuses for any impacted indents
            affected_indent_ids = (
                IndentItem.objects.filter(item_id=item_id, indent__status__in=["APPROVED", "PROCESSING"]).values_list("indent_id", flat=True).distinct()
            )
            for indent_id in affected_indent_ids:
                all_items = list(IndentItem.objects.filter(indent_id=indent_id))
                if not all_items:
                    continue
                complete = True
                for it in all_items:
                    req = Decimal(str(it.requested_qty or 0))
                    iss = Decimal(str(it.issued_qty or 0))
                    if iss < req:
                        complete = False
                        break
                if complete:
                    Indent.objects.filter(pk=indent_id).update(status="COMPLETED")
