import logging
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import F

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
            updated = Item.objects.filter(pk=item_id).update(
                current_stock=F("current_stock") + quantity_change
            )
            if not updated:
                logger.warning("Item %s not found", item_id)
                return False
            StockTransaction.objects.create(
                item_id=item_id,
                quantity_change=quantity_change,
                transaction_type=transaction_type,
                user_id=user_id,
                related_mrn=related_mrn,
                related_po_id=related_po_id,
                notes=notes,
            )
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error recording stock transaction: %s", exc)
        return False


def record_stock_transactions_bulk(transactions: List[Dict[str, Any]]) -> bool:
    try:
        with transaction.atomic():
            for tx in transactions:
                item_id = tx["item_id"]
                quantity_change = tx["quantity_change"]
                updated = Item.objects.filter(pk=item_id).update(
                    current_stock=F("current_stock") + quantity_change
                )
                if not updated:
                    logger.warning("Item %s not found", item_id)
                    raise ValueError("Stock transaction failed")
                StockTransaction.objects.create(
                    item_id=item_id,
                    quantity_change=quantity_change,
                    transaction_type=tx["transaction_type"],
                    user_id=tx.get("user_id"),
                    related_mrn=tx.get("related_mrn"),
                    related_po_id=tx.get("related_po_id"),
                    notes=tx.get("notes"),
                )
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Bulk stock transaction failed: %s", exc)
        return False


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
