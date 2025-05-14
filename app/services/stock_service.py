# app/services/stock_service.py
import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from datetime import date, timedelta, datetime

from sqlalchemy import text, exc as sqlalchemy_exc, inspect
from sqlalchemy.engine import Engine, Connection 
import traceback 

from app.db.database_utils import fetch_data
from app.services import item_service

def record_stock_transaction(
    item_id: int,
    quantity_change: float,
    transaction_type: str,
    user_id: Optional[str] = "System",
    related_mrn: Optional[str] = None,
    related_po_id: Optional[int] = None,
    notes: Optional[str] = None,
    db_engine_param: Optional[Engine] = None, 
    db_connection_param: Optional[Connection] = None 
) -> bool:
    
    active_connection_to_use: Optional[Connection] = None
    is_external_transaction = False

    if db_connection_param:
        # print(f"DEBUG (stock_service): Using provided db_connection_param for item {item_id}.") # Keep this if very granular debugging is needed
        active_connection_to_use = db_connection_param
        is_external_transaction = True 
    elif db_engine_param:
        # print(f"DEBUG (stock_service): Using provided db_engine_param for item {item_id} to create a new connection.")
        pass # Will create connection in the try block
    else:
        print("ERROR (stock_service): record_stock_transaction - Either db_engine_param or db_connection_param must be provided.")
        return False

    if not item_id:
        print("WARNING (stock_service): record_stock_transaction - Item ID missing. No transaction recorded.")
        return False

    notes_cleaned = str(notes).strip() if notes is not None and str(notes).strip() else None
    user_id_cleaned = str(user_id).strip() if user_id is not None and str(user_id).strip() else "System"
    related_mrn_cleaned = str(related_mrn).strip() if related_mrn is not None and str(related_mrn).strip() else None
    try:
        related_po_id_cleaned = int(related_po_id) if related_po_id is not None else None
    except ValueError:
        print(f"WARNING (stock_service): record_stock_transaction - Invalid related_po_id '{related_po_id}', setting to NULL.")
        related_po_id_cleaned = None

    stock_update_query = text("UPDATE items SET current_stock = COALESCE(current_stock, 0) + :quantity_change WHERE item_id = :item_id;")
    transaction_insert_query = text("""
        INSERT INTO stock_transactions
        (item_id, quantity_change, transaction_type, user_id, related_mrn, related_po_id, notes, transaction_date)
        VALUES
        (:item_id, :quantity_change, :transaction_type, :user_id, :related_mrn, :related_po_id, :notes, NOW());
    """)
    params_for_update = {"item_id": item_id, "quantity_change": quantity_change}
    params_for_insert = {
        "item_id": item_id, "quantity_change": quantity_change, "transaction_type": transaction_type,
        "user_id": user_id_cleaned, "related_mrn": related_mrn_cleaned,
        "related_po_id": related_po_id_cleaned, "notes": notes_cleaned
    }

    # Minimal print for normal operation path
    # print(f"DEBUG (stock_service): Processing stock for item_id: {item_id}, qty_change: {quantity_change}")
    
    current_stock_before = None # Initialize for wider scope if needed

    def _perform_db_operations(conn_obj: Connection):
        nonlocal current_stock_before 
        check_stock_query_local = text("SELECT current_stock FROM items WHERE item_id = :item_id") # Local definition
        try:
            if conn_obj.closed: print(f"DEBUG (stock_service): Connection object for stock check is closed for item {item_id}!")
            current_stock_result = conn_obj.execute(check_stock_query_local, {"item_id": item_id}).scalar_one_or_none()
            if current_stock_result is not None: current_stock_before = float(current_stock_result)
            # print(f"DEBUG (stock_service): Current stock for item {item_id} BEFORE update: {current_stock_before}")
        except Exception as e_stock_check:
            print(f"DEBUG (stock_service): Error checking current stock for item {item_id}: {e_stock_check}")
            raise 

        upd_result = conn_obj.execute(stock_update_query, params_for_update)
        # print(f"DEBUG (stock_service): item_id: {item_id}, upd_result.rowcount: {upd_result.rowcount if upd_result else 'upd_result_is_None'}")
        
        if upd_result is None or upd_result.rowcount == 0:
            item_exists_check = conn_obj.execute(text("SELECT 1 FROM items WHERE item_id = :item_id"), {"item_id": item_id}).scalar_one_or_none()
            err_msg_rowcount0 = f"Failed to update stock for item ID {item_id}. "
            if not item_exists_check: err_msg_rowcount0 += "(Item does NOT exist)."
            else: err_msg_rowcount0 += f"(Item exists, but rowcount is 0 - value might be unchanged or update prevented). Current stock before: {current_stock_before}, change attempted: {quantity_change}"
            raise sqlalchemy_exc.SQLAlchemyError(err_msg_rowcount0)
        
        conn_obj.execute(transaction_insert_query, params_for_insert)

    try:
        if is_external_transaction and active_connection_to_use:
            # print(f"DEBUG (stock_service): Executing DB operations with provided connection for item {item_id}.")
            _perform_db_operations(active_connection_to_use)
        elif db_engine_param: # This is the path that caused the AttributeError: 'Connection' object has no attribute 'connect'
                            # IF db_engine_param was actually a Connection object.
            # print(f"DEBUG (stock_service): Creating new connection and transaction from db_engine_param for item {item_id}.")
            if not isinstance(db_engine_param, Engine): # Add a check here
                print(f"CRITICAL ERROR (stock_service): db_engine_param is type {type(db_engine_param)}, not an Engine. This is unexpected.")
                # This indicates an issue in how this function was called.
                # Forcing failure if db_engine_param is not an actual Engine.
                raise TypeError(f"db_engine_param must be an Engine, got {type(db_engine_param)}")

            with db_engine_param.connect() as new_conn: # This line requires db_engine_param to be an Engine
                with new_conn.begin():
                    _perform_db_operations(new_conn)
        else:
            print("CRITICAL ERROR (stock_service): No valid engine or connection to use.")
            return False

        item_service.get_all_items_with_stock.clear()
        get_stock_transactions.clear()
        return True

    except sqlalchemy_exc.IntegrityError as ie:
        print(f"ERROR (stock_service): Database integrity error (item_id: {item_id}): {ie}\n{traceback.format_exc()}")
        if is_external_transaction: raise
        return False
    except sqlalchemy_exc.SQLAlchemyError as sqla_e:
        print(f"ERROR (stock_service): Database SQL error (item_id: {item_id}): {sqla_e}\n{traceback.format_exc()}")
        if is_external_transaction: raise
        return False
    except AttributeError as ae: 
        print(f"ERROR (stock_service): AttributeError encountered (item_id: {item_id}): {ae}\n{traceback.format_exc()}")
        if is_external_transaction: raise
        return False
    except Exception as e:
        print(f"ERROR (stock_service): Unexpected error (item_id: {item_id}): {e}")
        print(f"DEBUG (stock_service): Exception type: {type(e)}\n{traceback.format_exc()}")
        if is_external_transaction: raise
        return False

@st.cache_data(ttl=120, show_spinner="Fetching transaction history...")
def get_stock_transactions(
    _engine, 
    item_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    related_mrn: Optional[str] = None,
    related_po_id: Optional[int] = None
) -> pd.DataFrame:
    if _engine is None: return pd.DataFrame()
    query = """
        SELECT st.transaction_id, st.transaction_date, i.name AS item_name, i.unit AS item_unit, 
               st.transaction_type, st.quantity_change, st.user_id, st.notes, 
               st.related_mrn, st.related_po_id, st.item_id
        FROM stock_transactions st
        JOIN items i ON st.item_id = i.item_id
        WHERE 1=1
    """
    params: Dict[str, Any] = {} 

    if item_id is not None:
        query += " AND st.item_id = :item_id"; params['item_id'] = item_id
    if transaction_type:
        query += " AND st.transaction_type = :transaction_type"; params['transaction_type'] = transaction_type
    if user_id:
        query += " AND st.user_id ILIKE :user_id"; params['user_id'] = f"%{user_id}%"
    if related_mrn:
        query += " AND st.related_mrn ILIKE :related_mrn"; params['related_mrn'] = f"%{related_mrn}%"
    if related_po_id is not None:
        query += " AND st.related_po_id = :related_po_id"; params['related_po_id'] = related_po_id
    if start_date:
        query += " AND st.transaction_date >= :start_date"; params['start_date'] = start_date
    if end_date:
        effective_end_date = end_date + timedelta(days=1)
        query += " AND st.transaction_date < :end_date"; params['end_date'] = effective_end_date
    
    query += " ORDER BY st.transaction_date DESC, st.transaction_id DESC;"
    
    return fetch_data(_engine, query, params)