from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable, List, Optional

from django.db import transaction
from django.utils import timezone

from inventory.models import Indent, IndentItem, Item
from inventory.models.enums import ItemStatus

from . import stock_service
from .exceptions import StockServiceError


@dataclass
class IssueLine:
    indent_item_id: int
    issue_qty: Decimal
    source_location: str = ""


@dataclass
class IssueResult:
    ok: bool
    message: str
    updated_items: int = 0


def _as_decimal(val: Any) -> Decimal:
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0")


def _user_ident(user) -> tuple[str, Optional[int]]:
    try:
        uname = getattr(user, "username", None) or getattr(user, "email", None) or "System"
    except Exception:
        uname = "System"
    try:
        uid = getattr(user, "id", None)
    except Exception:
        uid = None
    return str(uname), uid


def issue_indent(indent_id: int, lines: Iterable[IssueLine], user) -> IssueResult:
    """Issue stock for an indent.

    - Validates pending quantities per IndentItem
    - Ensures sufficient current stock on Item
    - Records stock transactions with type "ISSUE" and related_indent_id
    - Updates IndentItem.issued_qty and item_status
    - Marks Indent COMPLETED when fully issued
    """

    indent = Indent.objects.select_for_update(of=("self",)).get(pk=indent_id)
    uname, uid = _user_ident(user)

    # Fetch all relevant IndentItems and Items in bulk
    by_id = {
        ii.indent_item_id: ii
        for ii in IndentItem.objects.select_for_update()
        .select_related("item")
        .filter(indent_id=indent_id)
    }

    updated = 0
    with transaction.atomic():
        for line in lines:
            qty = _as_decimal(getattr(line, "issue_qty", 0))
            if qty is None or qty <= 0:
                continue
            ii = by_id.get(getattr(line, "indent_item_id", 0))
            if not ii:
                continue
            req = _as_decimal(ii.requested_qty or 0)
            iss = _as_decimal(ii.issued_qty or 0)
            pending = req - iss
            if pending <= 0:
                continue
            if qty > pending:
                qty = pending
            item: Item = ii.item  # type: ignore
            current = _as_decimal(item.current_stock or 0)
            if current < qty:
                # Not enough stock; skip this line
                continue
            # Record stock movement (decrease)
            note_parts = [f"Issue for MRN {indent.mrn or indent.indent_id}"]
            loc = (getattr(line, "source_location", "") or "").strip()
            if loc:
                note_parts.append(f"from {loc}")
            try:
                stock_service.record_stock_transaction(
                    item_id=item.item_id,
                    quantity_change=-qty,
                    transaction_type="ISSUE",
                    user_id=uname,
                    user_int=uid,
                    related_indent_id=indent.indent_id,
                    notes=" ".join(note_parts),
                )
            except StockServiceError:
                # Skip on error; continue with others
                continue
            # Update issued quantity
            new_issued = iss + qty
            ii.issued_qty = new_issued
            if new_issued >= req:
                ii.item_status = ItemStatus.ISSUED
            ii.save(update_fields=["issued_qty", "item_status"])
            updated += 1

        # If all items fully issued, mark indent completed
        all_items = list(by_id.values())
        if all_items and all(
            _as_decimal(x.issued_qty or 0) >= _as_decimal(x.requested_qty or 0)
            for x in all_items
        ):
            indent.status = "COMPLETED"
            try:
                indent.processed_by = user
            except Exception:
                indent.processed_by = None
            indent.date_processed = timezone.now()
            indent.save(update_fields=["status", "processed_by", "date_processed", "updated_at"])  # type: ignore
        else:
            # If not completed and was SUBMITTED/APPROVED, set to PROCESSING to reflect progress
            if (indent.status or "").upper() in {"SUBMITTED", "APPROVED"}:
                indent.status = "PROCESSING"
                indent.save(update_fields=["status", "updated_at"])  # type: ignore

    if updated == 0:
        return IssueResult(ok=False, message="No items issued", updated_items=0)
    return IssueResult(ok=True, message=f"Issued {updated} line(s)", updated_items=updated)
