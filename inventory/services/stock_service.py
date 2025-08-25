import logging
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db import OperationalError, transaction
from django.db.models import F

from inventory.models import Item, StockTransaction

logger = logging.getLogger(__name__)


def record_stock_transaction(
    item_id: int,
    quantity_change: Decimal,
    transaction_type: str,
    user_id: Optional[str] = "System",
    user_int: Optional[int] = None,
    related_indent_id: Optional[int] = None,
    related_po_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> bool:
    quantity_change = Decimal(str(quantity_change))
    for attempt in range(5):
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
                    user_int=user_int,
                    related_indent_id=related_indent_id,
                    related_po_id=related_po_id,
                    notes=notes,
                )
            return True
        except OperationalError as exc:  # pragma: no cover - retry on lock
            logger.error("Error recording stock transaction: %s", exc)
            time.sleep(0.1 * attempt)
            continue
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error recording stock transaction: %s", exc)
            return False
    return False


def record_stock_transactions_bulk(transactions: List[Dict[str, Any]]) -> bool:
    try:
        with transaction.atomic():
            for tx in transactions:
                item_id = tx["item_id"]
                quantity_change = Decimal(str(tx["quantity_change"]))
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
                    user_int=tx.get("user_int"),
                    related_indent_id=tx.get("related_indent_id"),
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
                item.current_stock = (item.current_stock or Decimal("0")) - (
                    tx.quantity_change or Decimal("0")
                )
                item.save(update_fields=["current_stock"])
            StockTransaction.objects.filter(transaction_id__in=transaction_ids).delete()
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error removing stock transactions: %s", exc)
        return False


def get_stock_history(item_id: int, limit: int = 30) -> List[float]:
    """Return running stock levels for the most recent transactions."""

    txs = list(
        StockTransaction.objects.filter(item_id=item_id)
        .order_by("-transaction_date")
        .values_list("quantity_change", flat=True)[:limit]
    )[::-1]
    item = (
        Item.objects.filter(pk=item_id).values_list("current_stock", flat=True).first()
    )
    if item is None:
        return []
    current = item or Decimal("0")
    start = current - sum((tx or Decimal("0")) for tx in txs)
    history: List[float] = [float(start)]
    total = start
    for change in txs:
        total += change or Decimal("0")
        history.append(float(total))
    return history
