import logging
from typing import Dict, List, Optional, Tuple

from django.db import transaction
from inventory.models import Item, StockTransaction

logger = logging.getLogger(__name__)


def record_stock_transaction(
    item_id: int,
    quantity_change: float,
    transaction_type: str,
    user_id: Optional[str] = "System",
    related_mrn: Optional[str] = None,
    related_po_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> bool:
    try:
        with transaction.atomic():
            item = Item.objects.select_for_update().get(pk=item_id)
            item.current_stock = (item.current_stock or 0) + quantity_change
            item.save(update_fields=["current_stock"])
            StockTransaction.objects.create(
                item=item,
                quantity_change=quantity_change,
                transaction_type=transaction_type,
                user_id=user_id,
                related_mrn=related_mrn,
                related_po_id=related_po_id,
                notes=notes,
            )
        return True
    except Item.DoesNotExist:
        logger.warning("Item %s not found", item_id)
        return False
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error recording stock transaction: %s", exc)
        return False


def record_stock_transactions_bulk(transactions: List[Dict[str, any]]) -> bool:
    try:
        with transaction.atomic():
            for tx in transactions:
                if not record_stock_transaction(
                    item_id=tx["item_id"],
                    quantity_change=tx["quantity_change"],
                    transaction_type=tx["transaction_type"],
                    user_id=tx.get("user_id"),
                    related_mrn=tx.get("related_mrn"),
                    related_po_id=tx.get("related_po_id"),
                    notes=tx.get("notes"),
                ):
                    raise ValueError("Stock transaction failed")
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Bulk stock transaction failed: %s", exc)
        return False


from datetime import date

def remove_stock_transactions_bulk(transaction_ids: List[int]) -> bool:
    try:
        with transaction.atomic():
            txs = list(
                StockTransaction.objects.select_for_update().filter(
                    transaction_id__in=transaction_ids
                )
            )
            if len(txs) != len(transaction_ids):
                raise ValueError("One or more transactions not found")
            for tx in txs:
                item = Item.objects.select_for_update().get(pk=tx.item_id)
                item.current_stock = (item.current_stock or 0) - (tx.quantity_change or 0)
                item.save(update_fields=["current_stock"])
            StockTransaction.objects.filter(
                transaction_id__in=transaction_ids
            ).delete()
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error removing stock transactions: %s", exc)
        return False


def get_stock_transactions(
    item_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    related_mrn: Optional[str] = None,
    related_po_id: Optional[int] = None,
):
    """Fetches stock transaction records based on specified filters."""
    qs = StockTransaction.objects.select_related("item").all()

    if item_id is not None:
        qs = qs.filter(item_id=item_id)
    if transaction_type:
        qs = qs.filter(transaction_type=transaction_type)
    if user_id and user_id.strip():
        qs = qs.filter(user_id__icontains=user_id.strip())
    if related_mrn and related_mrn.strip():
        qs = qs.filter(related_mrn__icontains=related_mrn.strip())
    if related_po_id is not None:
        qs = qs.filter(related_po_id=related_po_id)
    if start_date:
        qs = qs.filter(transaction_date__date__gte=start_date)
    if end_date:
        qs = qs.filter(transaction_date__date__lte=end_date)

    return qs.order_by("-transaction_date", "-transaction_id")


def record_stock_transactions_bulk_with_status(
    transactions: List[Dict],
) -> Tuple[int, List[str]]:
    """Record stock transactions individually and report results."""
    if not transactions:
        return 0, ["No transactions provided."]

    success_count = 0
    errors: List[str] = []

    for idx, tx in enumerate(transactions):
        try:
            ok = record_stock_transaction(
                item_id=tx.get("item_id"),
                quantity_change=tx.get("quantity_change", 0),
                transaction_type=tx.get("transaction_type"),
                user_id=tx.get("user_id"),
                related_mrn=tx.get("related_mrn"),
                related_po_id=tx.get("related_po_id"),
                notes=tx.get("notes"),
            )
            if ok:
                success_count += 1
            else:
                errors.append(f"Row {idx}: failed to record transaction")
        except Exception as e:
            errors.append(f"Row {idx}: {e}")

    return success_count, errors
