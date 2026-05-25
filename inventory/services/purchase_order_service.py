import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db import IntegrityError, transaction
from django.db.models import Max, Sum

from inventory.forms.purchase_forms import PurchaseOrderForm, PurchaseOrderItemFormSet
from inventory.models import Item, PurchaseOrder, PurchaseOrderItem, Supplier

from .exceptions import PurchaseOrderServiceError
from .vendor_savings_service import create_po_estimated_savings

logger = logging.getLogger(__name__)

# Create uses ``create_po``; update uses ``ModelForm`` + formset save (stable line PKs).
# ``save_purchase_order_from_forms`` is the single entry point once forms are valid.


def generate_po_number() -> str:
    next_id = (PurchaseOrder.objects.aggregate(m=Max("po_id"))["m"] or 0) + 1
    return f"PO-{next_id:04d}"


def _po_header_dict_from_cleaned_form(form: PurchaseOrderForm) -> Dict[str, Any]:
    """Header fields for ``create_po`` (form must be valid)."""

    return {
        "supplier_id": form.cleaned_data["supplier"].pk,
        "order_date": form.cleaned_data["order_date"],
        "expected_delivery_date": form.cleaned_data.get("expected_delivery_date"),
        "status": form.cleaned_data.get("status"),
        "notes": form.cleaned_data.get("notes"),
    }


def _po_line_items_from_formset_cleaned(cleaned_rows: list) -> List[Dict[str, Any]]:
    """Line payloads for ``create_po`` from a validated ``PurchaseOrderItemFormSet``."""

    items_data: List[Dict[str, Any]] = []
    for row in cleaned_rows:
        if row and not row.get("DELETE", False):
            items_data.append(
                {
                    "item_id": row["item"].pk,
                    "quantity_ordered": row["quantity_ordered"],
                    "unit_price": row["unit_price"],
                }
            )
    return items_data


def save_purchase_order_from_forms(
    form: PurchaseOrderForm,
    formset: PurchaseOrderItemFormSet,
) -> PurchaseOrder:
    """Persist header and lines. Call only when ``form`` and ``formset`` are valid."""

    if form.instance.pk:
        with transaction.atomic():
            _validate_po_update_formset(formset)
            po = form.save()
            formset.save()
        return po

    po_data = _po_header_dict_from_cleaned_form(form)
    items_data = _po_line_items_from_formset_cleaned(formset.cleaned_data)
    po_id = create_po(po_data, items_data)
    return PurchaseOrder.objects.get(pk=po_id)


def _validate_po_update_formset(formset: PurchaseOrderItemFormSet) -> None:
    """Prevent edits that would detach or invalidate existing receipt history."""

    for item_form in formset.forms:
        if not getattr(item_form, "cleaned_data", None):
            continue
        po_item = item_form.instance
        if not po_item.pk:
            continue
        received_total = po_item.received_total
        if not received_total:
            continue
        item_name = getattr(getattr(po_item, "item", None), "name", "this item")
        if item_form.cleaned_data.get("DELETE"):
            raise PurchaseOrderServiceError(
                f"Cannot delete {item_name}; goods have already been received."
            )
        ordered_qty = item_form.cleaned_data.get("quantity_ordered")
        if ordered_qty is not None and ordered_qty < received_total:
            raise PurchaseOrderServiceError(
                (
                    f"Cannot reduce {item_name} below the already received "
                    f"quantity ({received_total})."
                )
            )


def create_po(po_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> int:
    """Create a purchase order and return its ID.

    Raises :class:`PurchaseOrderServiceError` if validation fails or the
    database operation cannot be completed.
    """

    required = ["supplier_id", "order_date"]
    missing = [f for f in required if not po_data.get(f)]
    if missing:
        raise PurchaseOrderServiceError(
            f"Missing required fields: {', '.join(missing)}"
        )
    if not items_data:
        raise PurchaseOrderServiceError(
            "Purchase Order must contain at least one item."
        )
    try:
        with transaction.atomic():
            supplier = Supplier.objects.get(pk=po_data["supplier_id"])
            item_ids = [int(i["item_id"]) for i in items_data]
            item_map = Item.objects.in_bulk(item_ids)
            po = PurchaseOrder.objects.create(
                po_number=po_data.get("po_number") or generate_po_number(),
                supplier=supplier,
                order_date=po_data["order_date"],
                expected_delivery_date=po_data.get("expected_delivery_date"),
                status=po_data.get("status", "DRAFT"),
                notes=po_data.get("notes"),
            )
            for item_d in items_data:
                item = item_map.get(int(item_d["item_id"]))
                if item is None:
                    raise Item.DoesNotExist(f"Item {item_d['item_id']} not found")
                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    item=item,
                    quantity_ordered=Decimal(str(item_d["quantity_ordered"])),
                    unit_price=Decimal(str(item_d["unit_price"])),
                )
            po_lines = [
                {
                    "item_id": int(item_d["item_id"]),
                    "quantity_ordered": Decimal(str(item_d["quantity_ordered"])),
                    "unit_price": Decimal(str(item_d["unit_price"])),
                    "fallback_price": item_map[
                        int(item_d["item_id"])
                    ].last_purchase_price
                    or item_map[int(item_d["item_id"])].initial_purchase_price
                    or Decimal("0"),
                }
                for item_d in items_data
            ]
            create_po_estimated_savings(
                po_id=po.po_id,
                po_date=po.order_date,
                supplier_id=supplier.pk,
                po_lines=po_lines,
            )
            return po.po_id
    except (Supplier.DoesNotExist, Item.DoesNotExist) as exc:
        raise PurchaseOrderServiceError(f"Invalid reference: {exc}") from exc
    except IntegrityError as exc:
        logger.error("Integrity error creating PO: %s", exc)
        raise PurchaseOrderServiceError(f"Database error: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error creating PO: %s", exc)
        raise PurchaseOrderServiceError(f"Database error: {exc}") from exc


def get_po_by_id(po_id: int) -> Optional[Dict[str, Any]]:
    try:
        po = PurchaseOrder.objects.select_related("supplier").get(pk=po_id)
    except PurchaseOrder.DoesNotExist:
        return None
    header = {
        "po_id": po.po_id,
        "po_number": po.po_number or f"PO-{po.po_id:04d}",
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


def get_orders_progress(po_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """Return totals and progress percentage for the given purchase orders.

    Args:
        po_ids: list of purchase order primary keys.

    Returns:
        Mapping of purchase order id to a dict with ``ordered_total``,
        ``received_total`` and ``percent`` keys.
    """
    if not po_ids:
        return {}
    rows = (
        PurchaseOrderItem.objects.filter(purchase_order_id__in=po_ids)
        .values("purchase_order_id")
        .annotate(
            ordered_total=Sum("quantity_ordered"),
            received_total=Sum("grnitem__quantity_received"),
        )
    )
    progress: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        ordered = r["ordered_total"] or Decimal("0")
        received = r["received_total"] or Decimal("0")
        percent = int(received / ordered * 100) if ordered else 0
        progress[r["purchase_order_id"]] = {
            "ordered_total": ordered,
            "received_total": received,
            "percent": percent,
        }
    return progress
