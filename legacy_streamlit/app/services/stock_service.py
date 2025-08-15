# app/services/stock_service.py
from datetime import date
import traceback
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
from . import cache_data
from sqlalchemy import text, exc as sqlalchemy_exc
from sqlalchemy.engine import Engine, Connection

from app.core.logging import get_logger
from app.db.database_utils import fetch_data

# Assuming item_service might be needed for future validation or fetching item names, though not directly used in current functions
# from app.services import item_service

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────
# STOCK TRANSACTION FUNCTIONS
# ─────────────────────────────────────────────────────────
def record_stock_transaction(
    item_id: int,
    quantity_change: float,
    transaction_type: str,
    user_id: Optional[str] = "System",
    related_mrn: Optional[str] = None,
    related_po_id: Optional[int] = None,
    notes: Optional[str] = None,
    db_engine_param: Optional[Engine] = None,
    db_connection_param: Optional[Connection] = None,
) -> bool:
    """
    Records a stock transaction and updates the item's current stock.
    Operates within an existing transaction if db_connection_param is provided,
    otherwise creates its own transaction using db_engine_param.
    Args:
        item_id: ID of the item.
        quantity_change: The change in quantity (positive for increase, negative for decrease).
        transaction_type: Type of transaction (e.g., RECEIVING, ADJUSTMENT).
        user_id: Identifier of the user performing the action.
        related_mrn: Related Material Request Number, if any.
        related_po_id: Related Purchase Order ID, if any.
        notes: Additional notes for the transaction.
        db_engine_param: SQLAlchemy Engine (used if db_connection_param is None).
        db_connection_param: Active SQLAlchemy Connection (if part of a larger transaction).
    Returns:
        True if successful, False otherwise.
    """
    active_connection_to_use: Optional[Connection] = None
    is_external_transaction = False

    if db_connection_param:
        active_connection_to_use = db_connection_param
        is_external_transaction = True
    elif db_engine_param:
        pass  # Will create connection in the try block
    else:
        logger.error(
            "ERROR [stock_service.record_stock_transaction]: Either db_engine_param or db_connection_param must be provided."
        )
        return False

    if not item_id:
        logger.warning(
            "WARNING [stock_service.record_stock_transaction]: Item ID missing. No transaction recorded."
        )
        return False

    notes_cleaned = (
        str(notes).strip() if notes is not None and str(notes).strip() else None
    )
    user_id_cleaned = (
        str(user_id).strip()
        if user_id is not None and str(user_id).strip()
        else "System"
    )
    related_mrn_cleaned = (
        str(related_mrn).strip()
        if related_mrn is not None and str(related_mrn).strip()
        else None
    )

    related_po_id_cleaned: Optional[int] = None
    if related_po_id is not None:
        try:
            related_po_id_cleaned = int(related_po_id)
        except ValueError:
            logger.warning(
                "WARNING [stock_service.record_stock_transaction]: Invalid related_po_id '%s', will be stored as NULL.",
                related_po_id,
            )
            # related_po_id_cleaned remains None

    stock_update_query = text(
        "UPDATE items SET current_stock = COALESCE(current_stock, 0) + :quantity_change, updated_at = NOW() WHERE item_id = :item_id;"
    )
    transaction_insert_query = text(
        """
        INSERT INTO stock_transactions
        (item_id, quantity_change, transaction_type, user_id, related_mrn, related_po_id, notes, transaction_date)
        VALUES
        (:item_id, :quantity_change, :transaction_type, :user_id, :related_mrn, :related_po_id, :notes, NOW());
    """
    )
    params_for_update = {"item_id": item_id, "quantity_change": quantity_change}
    params_for_insert = {
        "item_id": item_id,
        "quantity_change": quantity_change,
        "transaction_type": transaction_type,
        "user_id": user_id_cleaned,
        "related_mrn": related_mrn_cleaned,
        "related_po_id": related_po_id_cleaned,
        "notes": notes_cleaned,
    }

    current_stock_before: Optional[float] = None

    def _perform_db_operations(conn_obj: Connection):
        nonlocal current_stock_before
        check_stock_query_local = text(
            "SELECT current_stock FROM items WHERE item_id = :item_id"
        )
        try:
            if conn_obj.closed:  # Should ideally not happen if managed correctly
                logger.warning(
                    "WARNING [stock_service._perform_db_operations]: Connection object for stock check is closed for item %s!",
                    item_id,
                )
                # Depending on desired robustness, could try to re-establish or fail.
                # For now, let it proceed and potentially fail at execute if truly closed.
            current_stock_result = conn_obj.execute(
                check_stock_query_local, {"item_id": item_id}
            ).scalar_one_or_none()
            if current_stock_result is not None:
                current_stock_before = float(current_stock_result)
        except Exception as e_stock_check:
            logger.error(
                "ERROR [stock_service._perform_db_operations]: Error checking current stock for item %s: %s",
                item_id,
                e_stock_check,
            )
            raise  # Re-raise to be caught by outer try-except, ensuring transaction rollback

        upd_result = conn_obj.execute(stock_update_query, params_for_update)

        if (
            upd_result.rowcount == 0
        ):  # upd_result should not be None if execute is successful
            item_exists_check_res = conn_obj.execute(
                text("SELECT 1 FROM items WHERE item_id = :item_id"),
                {"item_id": item_id},
            ).scalar_one_or_none()
            err_msg_rowcount0 = f"Failed to update stock for item ID {item_id}. "
            if not item_exists_check_res:
                err_msg_rowcount0 += "(Item does NOT exist)."
            else:
                err_msg_rowcount0 += f"(Item exists, but no rows affected. Current stock: {current_stock_before}, change attempted: {quantity_change})."
            raise sqlalchemy_exc.SQLAlchemyError(err_msg_rowcount0)  # Raise to rollback

        conn_obj.execute(transaction_insert_query, params_for_insert)

    try:
        if is_external_transaction and active_connection_to_use:
            _perform_db_operations(active_connection_to_use)
        elif db_engine_param:
            if not isinstance(db_engine_param, Engine):
                # This critical check was good to keep
                raise TypeError(
                    f"db_engine_param must be an Engine instance, got {type(db_engine_param)}"
                )

            with db_engine_param.connect() as new_conn:
                with new_conn.begin():  # This starts a new transaction
                    _perform_db_operations(new_conn)
        else:
            # This case should not be reached if the initial checks for params are done.
            logger.critical(
                "CRITICAL ERROR [stock_service.record_stock_transaction]: No valid database engine or connection provided."
            )
            return False

        # Clear relevant caches that depend on stock levels or transaction history
        # Example: from app.services import item_service (if item_service had relevant caches)
        # item_service.get_all_items_with_stock.clear() # Assuming get_all_items_with_stock is affected
        get_stock_transactions.clear()  # Defined below, depends on this data

        # Also clear item_service cache as stock levels change
        # This requires item_service to be imported.
        # For loose coupling, this clear could be signaled differently, but for now, direct clear is acceptable.
        try:
            from app.services import item_service

            item_service.get_all_items_with_stock.clear()
        except ImportError:
            logger.warning(
                "WARNING [stock_service.record_stock_transaction]: Could not import item_service to clear its cache."
            )

        return True

    except sqlalchemy_exc.IntegrityError as ie:
        logger.error(
            "ERROR [stock_service.record_stock_transaction]: Database integrity error for item_id %s: %s\n%s",
            item_id,
            ie,
            traceback.format_exc(),
        )
        if is_external_transaction:
            raise  # Propagate if part of a larger transaction
        return False
    except sqlalchemy_exc.SQLAlchemyError as sqla_e:  # More general SQLAlchemy errors
        logger.error(
            "ERROR [stock_service.record_stock_transaction]: Database SQL error for item_id %s: %s\n%s",
            item_id,
            sqla_e,
            traceback.format_exc(),
        )
        if is_external_transaction:
            raise
        return False
    except TypeError as te:  # Catching the TypeError we might raise
        logger.error(
            "ERROR [stock_service.record_stock_transaction]: Type error for item_id %s: %s\n%s",
            item_id,
            te,
            traceback.format_exc(),
        )
        if is_external_transaction:
            raise
        return False
    except Exception as e:  # Catch-all for other unexpected errors
        logger.error(
            "ERROR [stock_service.record_stock_transaction]: Unexpected error for item_id %s: %s\nType: %s\n%s",
            item_id,
            e,
            type(e),
            traceback.format_exc(),
        )
        if is_external_transaction:
            raise
        return False


def record_stock_transactions_bulk(
    db_engine: Engine, transactions: List[Dict]
) -> bool:
    """Record multiple stock transactions inside a single DB transaction.

    Args:
        db_engine: SQLAlchemy Engine instance.
        transactions: List of transaction dictionaries accepted by
            :func:`record_stock_transaction`.

    Returns:
        True if all transactions are recorded successfully, otherwise False.
    """
    if not transactions:
        return True

    try:
        with db_engine.begin() as conn:
            for tx in transactions:
                success = record_stock_transaction(
                    item_id=tx.get("item_id"),
                    quantity_change=tx.get("quantity_change", 0),
                    transaction_type=tx.get("transaction_type"),
                    user_id=tx.get("user_id"),
                    related_mrn=tx.get("related_mrn"),
                    related_po_id=tx.get("related_po_id"),
                    notes=tx.get("notes"),
                    db_connection_param=conn,
                )
                if not success:
                    raise sqlalchemy_exc.SQLAlchemyError(
                        "Failed to record stock transaction"
                    )
        return True
    except Exception as e:
        logger.error(
            "ERROR [stock_service.record_stock_transactions_bulk]: %s", e
        )
        return False


def record_stock_transactions_bulk_with_status(
    db_engine: Engine, transactions: List[Dict]
) -> Tuple[int, List[str]]:
    """Record stock transactions individually and report results.

    Each transaction is committed separately so that one failing row does not
    prevent others from being saved.

    Args:
        db_engine: SQLAlchemy Engine instance.
        transactions: List of transaction dictionaries accepted by
            :func:`record_stock_transaction`.

    Returns:
        A tuple ``(success_count, errors)`` where ``errors`` contains messages
        for rows that could not be processed.
    """
    if db_engine is None:
        return 0, ["Database engine not available."]
    if not transactions:
        return 0, ["No transactions provided."]

    success_count = 0
    errors: List[str] = []

    for idx, tx in enumerate(transactions):
        try:
            with db_engine.begin() as conn:
                ok = record_stock_transaction(
                    item_id=tx.get("item_id"),
                    quantity_change=tx.get("quantity_change", 0),
                    transaction_type=tx.get("transaction_type"),
                    user_id=tx.get("user_id"),
                    related_mrn=tx.get("related_mrn"),
                    related_po_id=tx.get("related_po_id"),
                    notes=tx.get("notes"),
                    db_connection_param=conn,
                )
            if ok:
                success_count += 1
            else:
                errors.append(f"Row {idx}: failed to record transaction")
        except Exception as e:  # pylint: disable=broad-except
            errors.append(f"Row {idx}: {e}")

    return success_count, errors


def remove_stock_transactions_bulk(
    db_engine: Engine, transaction_ids: List[int]
) -> bool:
    """Remove multiple stock transactions and reverse their stock effects.

    Args:
        db_engine: SQLAlchemy Engine instance.
        transaction_ids: List of transaction IDs to remove.

    Returns:
        True if all removals succeed, otherwise False.
    """
    if not transaction_ids:
        return True

    select_query = text(
        "SELECT item_id, quantity_change FROM stock_transactions WHERE transaction_id = :tid"
    )
    update_query = text(
        "UPDATE items SET current_stock = COALESCE(current_stock, 0) - :qty, updated_at = NOW() WHERE item_id = :item_id"
    )
    delete_query = text(
        "DELETE FROM stock_transactions WHERE transaction_id = :tid"
    )

    try:
        with db_engine.begin() as conn:
            for tid in transaction_ids:
                row = conn.execute(select_query, {"tid": tid}).fetchone()
                if row is None:
                    raise ValueError(f"Transaction ID {tid} does not exist")
                item_id, qty = row
                upd_result = conn.execute(
                    update_query, {"qty": qty, "item_id": item_id}
                )
                if upd_result.rowcount == 0:
                    raise sqlalchemy_exc.SQLAlchemyError(
                        f"Failed to update item {item_id} when removing transaction {tid}"
                    )
                del_result = conn.execute(delete_query, {"tid": tid})
                if del_result.rowcount == 0:
                    raise sqlalchemy_exc.SQLAlchemyError(
                        f"Failed to delete transaction {tid}"
                    )

        # Clear caches that depend on these tables
        get_stock_transactions.clear()
        try:
            from app.services import item_service

            item_service.get_all_items_with_stock.clear()
        except ImportError:
            logger.warning(
                "WARNING [stock_service.remove_stock_transactions_bulk]: Could not import item_service to clear its cache."
            )

        return True
    except Exception as e:
        logger.error(
            "ERROR [stock_service.remove_stock_transactions_bulk]: %s", e
        )
        return False


@cache_data(ttl=120, show_spinner="Fetching transaction history...")
def get_stock_transactions(
    _engine: Engine,
    item_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    user_id: Optional[str] = None,  # Assuming this is a search term (contains)
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    related_mrn: Optional[str] = None,  # Assuming this is a search term (contains)
    related_po_id: Optional[int] = None,
) -> pd.DataFrame:
    """
    Fetches stock transaction records based on specified filters.
    Args:
        _engine: SQLAlchemy database engine instance.
        item_id: Filter by item ID.
        transaction_type: Filter by transaction type.
        user_id: Filter by user ID (case-insensitive, contains).
        start_date: Filter by start date of transaction.
        end_date: Filter by end date of transaction.
        related_mrn: Filter by related MRN (case-insensitive, contains).
        related_po_id: Filter by related PO ID.
    Returns:
        Pandas DataFrame of stock transactions.
    """
    if _engine is None:
        logger.error(
            "ERROR [stock_service.get_stock_transactions]: Database engine not available."
        )
        return pd.DataFrame()

    query = """
        SELECT st.transaction_id, st.transaction_date, i.name AS item_name, i.base_unit AS item_unit,
               st.transaction_type, st.quantity_change, st.user_id, st.notes,
               st.related_mrn, st.related_po_id, st.item_id
        FROM stock_transactions st
        JOIN items i ON st.item_id = i.item_id
        WHERE 1=1
    """
    params: Dict[str, Any] = {}

    if item_id is not None:
        query += " AND st.item_id = :item_id"
        params["item_id"] = item_id
    if transaction_type:
        query += " AND st.transaction_type = :transaction_type"
        params["transaction_type"] = transaction_type
    if user_id and user_id.strip():  # Search if user_id is provided
        query += " AND st.user_id ILIKE :user_id"
        params["user_id"] = f"%{user_id.strip()}%"
    if related_mrn and related_mrn.strip():  # Search if related_mrn is provided
        query += " AND st.related_mrn ILIKE :related_mrn"
        params["related_mrn"] = f"%{related_mrn.strip()}%"
    if related_po_id is not None:  # Exact match for PO ID
        query += " AND st.related_po_id = :related_po_id"
        params["related_po_id"] = related_po_id
    if start_date:
        # Ensure transaction_date is compared as DATE if start_date is just a date
        query += " AND DATE(st.transaction_date) >= :start_date"
        params["start_date"] = start_date
    if end_date:
        # Ensure transaction_date is compared as DATE if end_date is just a date
        # To include the whole end_date, the condition should be st.transaction_date < end_date + 1 day
        # Or DATE(st.transaction_date) <= :end_date
        query += " AND DATE(st.transaction_date) <= :end_date"
        params["end_date"] = end_date

    query += " ORDER BY st.transaction_date DESC, st.transaction_id DESC;"

    return fetch_data(_engine, query, params)
