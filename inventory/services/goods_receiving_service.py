import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Max

from inventory.models import (
    GRNItem,
    GoodsReceivedNote,
    Item,
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
)
from . import stock_service

logger = logging.getLogger(__name__)


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
        PurchaseOrder.objects.get(pk=grn_data.get("po_id"))
        if grn_data.get("po_id")
        else None
    )
    grn = GoodsReceivedNote.objects.create(
        purchase_order=po,
        supplier=supplier,
        received_date=grn_data["received_date"],
        notes=grn_data.get("notes"),
    )
    return grn, po


def _process_items(
    grn: GoodsReceivedNote,
    items_received_data: List[Dict[str, Any]],
    user_id: str,
    po: Optional[PurchaseOrder],
) -> None:
    grn_number = generate_grn_number()
    for item_d in items_received_data:
        item = Item.objects.get(pk=item_d["item_id"])
        po_item = PurchaseOrderItem.objects.get(pk=item_d["po_item_id"])
        qty = float(item_d["quantity_received"])
        GRNItem.objects.create(
            grn=grn,
            po_item=po_item,
            quantity_ordered_on_po=item_d.get(
                "quantity_ordered_on_po", po_item.quantity_ordered
            ),
            quantity_received=qty,
            unit_price_at_receipt=Decimal(str(item_d["unit_price_at_receipt"])),
            item_notes=item_d.get("item_notes"),
        )
        po_item.quantity_received += qty
        po_item.save()
        stock_service.record_stock_transaction(
            item_id=item.item_id,
            quantity_change=qty,
            transaction_type="RECEIVING",
            user_id=user_id,
            related_po_id=po.po_id if po else None,
            notes=f"GRN {grn_number}",
        )
    if po:
        _update_po_status(po)


def _update_po_status(po: PurchaseOrder) -> None:
    fully_received = all(
        i.quantity_received >= i.quantity_ordered
        for i in po.purchaseorderitem_set.all()
    )
    po.status = "COMPLETE" if fully_received else "PARTIAL"
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
    ) as exc:
        return False, f"Invalid reference: {exc}", None
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error creating GRN: %s", exc)
        return False, "Database error creating GRN.", None
