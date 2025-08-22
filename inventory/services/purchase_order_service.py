import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Max, Sum

from inventory.models import Item, PurchaseOrder, PurchaseOrderItem, Supplier

logger = logging.getLogger(__name__)


def generate_po_number() -> str:
    next_id = (PurchaseOrder.objects.aggregate(m=Max("po_id"))["m"] or 0) + 1
    return f"PO-{next_id:04d}"


def create_po(
    po_data: Dict[str, Any], items_data: List[Dict[str, Any]]
) -> Tuple[bool, str, Optional[int]]:
    required = ["supplier_id", "order_date"]
    missing = [f for f in required if not po_data.get(f)]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}", None
    if not items_data:
        return False, "Purchase Order must contain at least one item.", None
    try:
        with transaction.atomic():
            supplier = Supplier.objects.get(pk=po_data["supplier_id"])
            po = PurchaseOrder.objects.create(
                supplier=supplier,
                order_date=po_data["order_date"],
                expected_delivery_date=po_data.get("expected_delivery_date"),
                status=po_data.get("status", "DRAFT"),
                notes=po_data.get("notes"),
            )
            for item_d in items_data:
                item = Item.objects.get(pk=item_d["item_id"])
                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    item=item,
                    quantity_ordered=Decimal(str(item_d["quantity_ordered"])),
                    unit_price=Decimal(str(item_d["unit_price"])),
                )
            return True, "Purchase Order created", po.po_id
    except (Supplier.DoesNotExist, Item.DoesNotExist) as exc:
        return False, f"Invalid reference: {exc}", None
    except IntegrityError as exc:
        logger.error("Integrity error creating PO: %s", exc)
        return False, "Database error creating Purchase Order.", None
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error creating PO: %s", exc)
        return False, "Database error creating Purchase Order.", None


def get_po_by_id(po_id: int) -> Optional[Dict[str, Any]]:
    try:
        po = PurchaseOrder.objects.select_related("supplier").get(pk=po_id)
    except PurchaseOrder.DoesNotExist:
        return None
    header = {
        "po_id": po.po_id,
        "po_number": generate_po_number() if po.po_id is None else f"PO-{po.po_id:04d}",
        "supplier_id": po.supplier_id,
        "supplier_name": po.supplier.name,
        "order_date": po.order_date,
        "expected_delivery_date": po.expected_delivery_date,
        "status": po.status,
        "notes": po.notes,
    }
    items = list(
        PurchaseOrderItem.objects.filter(purchase_order=po)
        .select_related("item")
        .annotate(_received_total=Sum("grnitem__quantity_received"))
        .values(
            "po_item_id",
            "item_id",
            "item__name",
            "quantity_ordered",
            "_received_total",
            "unit_price",
        )
    )
    header["items"] = [
        {
            "po_item_id": i["po_item_id"],
            "item_id": i["item_id"],
            "item_name": i["item__name"],
            "quantity_ordered": i["quantity_ordered"],
            "received_total": i["_received_total"] or Decimal("0"),
            "unit_price": i["unit_price"],
        }
        for i in items
    ]
    return header
