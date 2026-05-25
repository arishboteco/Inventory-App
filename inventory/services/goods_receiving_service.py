import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Max, Sum

from inventory.models import (
    GoodsReceivedNote,
    GRNItem,
    Item,
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
)

from . import indent_consolidation_service, stock_service
from .exceptions import StockServiceError
from .vendor_savings_service import apply_grn_realization

logger = logging.getLogger(__name__)
RECEIVABLE_STATUSES = {"SENT", "RECEIVED"}


def generate_grn_number() -> str:
    next_id = (GoodsReceivedNote.objects.aggregate(m=Max("grn_id"))["m"] or 0) + 1
    return f"GRN-{next_id:04d}"


def _validate_inputs(
    grn_data: Dict[str, Any], items_received_data: List[Dict[str, Any]]
) -> Tuple[bool, str]:
    required = ["supplier_id", "received_date", "received_by_user_id"]
    missing = [f for f in required if not grn_data.get(f)]
    if missing:
        return False, f"Missing GRN fields: {', '.join(missing)}"
    if not items_received_data:
        return False, "GRN must contain at least one received item."
    return True, ""


def _create_grn_header(
    grn_data: Dict[str, Any],
) -> Tuple[GoodsReceivedNote, Optional[PurchaseOrder]]:
    supplier = Supplier.objects.get(pk=grn_data["supplier_id"])
    po = (
        PurchaseOrder.objects.select_for_update().get(pk=grn_data.get("po_id"))
        if grn_data.get("po_id")
        else None
    )
    if po and po.status not in RECEIVABLE_STATUSES:
        raise ValueError("Only sent purchase orders can receive goods.")
    grn = GoodsReceivedNote.objects.create(
        grn_number=generate_grn_number(),
        purchase_order=po,
        supplier=supplier,
        received_date=grn_data["received_date"],
        notes=grn_data.get("notes"),
        attachment=grn_data.get("attachment"),
    )
    return grn, po


def _process_items(
    grn: GoodsReceivedNote,
    items_received_data: List[Dict[str, Any]],
    user_id: str,
    po: Optional[PurchaseOrder],
) -> None:
    grn_number = grn.grn_number
    item_ids = {d["item_id"] for d in items_received_data}
    po_item_ids = {d["po_item_id"] for d in items_received_data}
    items = Item.objects.in_bulk(item_ids)
    po_items = PurchaseOrderItem.objects.select_for_update().in_bulk(po_item_ids)
    remaining_by_po_item: dict[int, Decimal] = {}
    for po_item_id, po_item in po_items.items():
        remaining_by_po_item[po_item_id] = max(
            Decimal("0"),
            (po_item.quantity_ordered or Decimal("0")) - po_item.received_total,
        )

    grn_items: List[GRNItem] = []
    for item_d in items_received_data:
        item = items.get(item_d["item_id"])
        if item is None:
            raise Item.DoesNotExist(f"Item {item_d['item_id']} not found")
        po_item = po_items.get(item_d["po_item_id"])
        if po_item is None:
            raise PurchaseOrderItem.DoesNotExist(
                f"PurchaseOrderItem {item_d['po_item_id']} not found"
            )
        if po and po_item.purchase_order_id != po.pk:
            raise ValueError("Received line does not belong to this purchase order.")
        if po_item.item_id != item.item_id:
            raise ValueError("Received line item does not match the purchase order.")
        qty = Decimal(str(item_d["quantity_received"]))
        if qty <= 0:
            raise ValueError(f"Received quantity for {item.name} must be positive.")
        remaining = remaining_by_po_item.get(po_item.pk, Decimal("0"))
        if qty > remaining:
            raise ValueError(
                f"Received quantity for {item.name} exceeds remaining quantity."
            )
        remaining_by_po_item[po_item.pk] = remaining - qty
        grn_items.append(
            GRNItem(
                grn=grn,
                po_item=po_item,
                item=item,
                quantity_ordered_on_po=Decimal(
                    str(item_d.get("quantity_ordered_on_po", po_item.quantity_ordered))
                ),
                quantity_received=qty,
                unit_price_at_receipt=Decimal(str(item_d["unit_price_at_receipt"])),
                item_notes=item_d.get("item_notes"),
            )
        )
        stock_service.record_stock_transaction(
            item_id=item.item_id,
            quantity_change=qty,
            transaction_type="RECEIVING",
            user_id=user_id,
            related_po_id=po.po_id if po else None,
            notes=f"GRN {grn_number}",
        )
        if po:
            apply_grn_realization(
                po_id=po.po_id,
                item_id=item.item_id,
                quantity_received=qty,
                invoice_price=item_d["unit_price_at_receipt"],
            )

    GRNItem.objects.bulk_create(grn_items)
    # Apply received quantities to pending indents for fulfillment roll-up
    try:
        receipts = [
            {
                "item_id": gi.po_item.item_id,
                "quantity_received": gi.quantity_received,
            }
            for gi in grn_items
        ]
        indent_consolidation_service.apply_receipts_to_indents(receipts)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to allocate receipts to indents: %s", exc)
    if po:
        _update_po_status(po)


def _update_po_status(po: PurchaseOrder) -> None:
    fully_received = all(
        i.received_total >= i.quantity_ordered
        for i in po.purchaseorderitem_set.annotate(
            _received_total=Sum("grnitem__quantity_received")
        )
    )
    po.status = "RECEIVED" if fully_received else "SENT"
    po.save()


def create_grn(
    grn_data: Dict[str, Any], items_received_data: List[Dict[str, Any]]
) -> Tuple[bool, str, Optional[int]]:
    valid, msg = _validate_inputs(grn_data, items_received_data)
    if not valid:
        return False, msg, None
    try:
        with transaction.atomic():
            grn, po = _create_grn_header(grn_data)
            _process_items(
                grn, items_received_data, grn_data["received_by_user_id"], po
            )
            return True, "GRN created", grn.grn_id
    except (
        Supplier.DoesNotExist,
        Item.DoesNotExist,
        PurchaseOrderItem.DoesNotExist,
        StockServiceError,
    ) as exc:
        return False, f"Invalid reference: {exc}", None
    except ValueError as exc:
        return False, str(exc), None
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error creating GRN: %s", exc)
        return False, "Database error creating GRN.", None
