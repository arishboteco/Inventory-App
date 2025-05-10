# app/services/stock_service.py
import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple # Ensure all needed types are here
from datetime import date, timedelta # For get_stock_transactions

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.database_utils import fetch_data
from app.services import item_service # Needed to clear item cache

# ─────────────────────────────────────────────────────────
# STOCK TRANSACTION FUNCTIONS
# ─────────────────────────────────────────────────────────
def record_stock_transaction(
    engine, item_id: int, quantity_change: float, transaction_type: str,
    user_id: Optional[str] = "System", related_mrn: Optional[str] = None,
    related_po_id: Optional[int] = None, notes: Optional[str] = None
) -> bool:
    if engine is None: return False
    if not item_id or quantity_change == 0:
        st.warning("Item ID missing or quantity change is zero. No transaction recorded.")
        return False
    notes_cleaned = str(notes).strip() if notes is not None else None
    user_id_cleaned = str(user_id).strip() if user_id is not None else "System"
    related_mrn_cleaned = str(related_mrn).strip() if related_mrn is not None else None

    stock_update_query = text("UPDATE items SET current_stock = COALESCE(current_stock, 0) + :quantity_change WHERE item_id = :item_id;")
    transaction_insert_query = text("""
        INSERT INTO stock_transactions (item_id, quantity_change, transaction_type, user_id, related_mrn, related_po_id, notes, transaction_date)
        VALUES (:item_id, :quantity_change, :transaction_type, :user_id, :related_mrn, :related_po_id, :notes, NOW());
    """)
    params = {
        "item_id": item_id, "quantity_change": quantity_change, "transaction_type": transaction_type,
        "user_id": user_id_cleaned, "related_mrn": related_mrn_cleaned,
        "related_po_id": related_po_id, "notes": notes_cleaned
    }
    try:
        with engine.connect() as connection:
            with connection.begin():
                upd_result = connection.execute(stock_update_query, {"item_id": item_id, "quantity_change": quantity_change})
                if upd_result.rowcount == 0:
                     raise Exception(f"Failed to update stock for item ID {item_id} (item might not exist).")
                connection.execute(transaction_insert_query, params)
        # Clear relevant caches
        item_service.get_all_items_with_stock.clear() # Item stock has changed
        get_stock_transactions.clear() # This service's own cache for transaction history
        return True
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error recording stock transaction: {e}")
        return False

@st.cache_data(ttl=120, show_spinner="Fetching transaction history...")
def get_stock_transactions(
    _engine, item_id: Optional[int] = None, transaction_type: Optional[str] = None,
    user_id: Optional[str] = None, start_date: Optional[date] = None,
    end_date: Optional[date] = None, related_mrn: Optional[str] = None
) -> pd.DataFrame:
    if _engine is None: return pd.DataFrame()
    query = """
        SELECT st.transaction_id, st.transaction_date, i.name AS item_name, st.transaction_type,
               st.quantity_change, st.user_id, st.notes, st.related_mrn, st.related_po_id, st.item_id
        FROM stock_transactions st JOIN items i ON st.item_id = i.item_id WHERE 1=1
    """
    params = {}
    if item_id: query += " AND st.item_id = :item_id"; params['item_id'] = item_id
    if transaction_type: query += " AND st.transaction_type = :transaction_type"; params['transaction_type'] = transaction_type
    if user_id: query += " AND st.user_id ILIKE :user_id"; params['user_id'] = f"%{user_id}%"
    if related_mrn: query += " AND st.related_mrn ILIKE :related_mrn"; params['related_mrn'] = f"%{related_mrn}%"
    if start_date: query += " AND st.transaction_date >= :start_date"; params['start_date'] = start_date
    if end_date:
        effective_end_date = end_date + timedelta(days=1)
        query += " AND st.transaction_date < :end_date"; params['end_date'] = effective_end_date
    query += " ORDER BY st.transaction_date DESC, st.transaction_id DESC;"
    return fetch_data(_engine, query, params)