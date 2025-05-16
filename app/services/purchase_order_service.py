# app/services/purchase_order_service.py
from datetime import datetime
import traceback 
from typing import Optional, Dict, List, Tuple, Any

import pandas as pd
import streamlit as st # For type hinting @st.cache_data
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError 
from sqlalchemy.engine import Engine

from app.db.database_utils import fetch_data
from app.core.constants import ( 
    PO_STATUS_DRAFT, PO_STATUS_ORDERED, PO_STATUS_FULLY_RECEIVED,
    PO_STATUS_PARTIALLY_RECEIVED, PO_STATUS_CANCELLED, ALL_PO_STATUSES
)

# ─────────────────────────────────────────────────────────
# PURCHASE ORDER (PO) FUNCTIONS
# ─────────────────────────────────────────────────────────
def generate_po_number(engine: Engine) -> Optional[str]:
    """
    Generates a new Purchase Order (PO) number using a database sequence.
    Args:
        engine: SQLAlchemy database engine instance.
    Returns:
        Formatted PO number string or None on failure.
    """
    if engine is None:
        print("ERROR [purchase_order_service.generate_po_number]: Database engine not available.")
        return None
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT nextval('po_sequence');"))
            seq_num = result.scalar_one()
            return f"PO-{seq_num:04d}" # Assumes 4-digit padding
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR [purchase_order_service.generate_po_number]: Error generating PO Number: {e}\n{traceback.format_exc()}")
        return None

@st.cache_data(ttl=300, show_spinner="Fetching Purchase Orders...")
def list_pos(_engine: Engine, filters: Optional[Dict[str, Any]] = None, sort_by: Optional[str] = None) -> pd.DataFrame:
    """
    Lists Purchase Orders based on filters and sorting criteria.
    Args:
        _engine: SQLAlchemy database engine instance.
        filters: Dictionary of filters to apply.
        sort_by: Column name to sort by, optionally with ASC/DESC.
    Returns:
        Pandas DataFrame of Purchase Orders.
    """
    if _engine is None:
        print("ERROR [purchase_order_service.list_pos]: Database engine not available.")
        return pd.DataFrame()
        
    query_str = """
        SELECT po.po_id, po.po_number, po.supplier_id, s.name AS supplier_name, 
               po.order_date, po.expected_delivery_date, po.status, po.total_amount, 
               po.created_by_user_id, po.created_at, po.updated_at, po.notes
        FROM purchase_orders po
        JOIN suppliers s ON po.supplier_id = s.supplier_id
        WHERE 1=1
    """
    params: Dict[str, Any] = {}
    if filters:
        if "status" in filters and filters["status"]:
            query_str += " AND po.status = :status"; params["status"] = filters["status"]
        if "supplier_id" in filters and filters["supplier_id"]:
            query_str += " AND po.supplier_id = :supplier_id"; params["supplier_id"] = filters["supplier_id"]
        if "po_number_ilike" in filters and filters["po_number_ilike"] and filters["po_number_ilike"].strip():
            query_str += " AND po.po_number ILIKE :po_number_ilike"; params["po_number_ilike"] = f"%{filters['po_number_ilike'].strip()}%"
    
    valid_sort_cols = ["po_id", "po_number", "supplier_name", "order_date", "expected_delivery_date", "status", "total_amount", "created_at", "updated_at"]
    default_sort = " ORDER BY po.order_date DESC, po.created_at DESC"
    
    if sort_by and sort_by.strip():
        # Basic validation: ensure the column part of sort_by is valid
        sort_col_candidate = sort_by.strip().split(" ")[0].lower()
        # Remove potential table prefix if present (e.g., "po.order_date" -> "order_date")
        if '.' in sort_col_candidate:
            sort_col_candidate = sort_col_candidate.split('.')[1]
            
        if sort_col_candidate in valid_sort_cols:
             # Use the user-provided sort_by directly to allow ASC/DESC specification
             # Ensure the table alias 'po.' is used if not already in sort_by for safety
             if not sort_by.lower().startswith("po.") and sort_col_candidate in ["po_id", "po_number", "order_date", "expected_delivery_date", "status", "total_amount", "created_at", "updated_at"]:
                 query_str += f" ORDER BY po.{sort_by.strip()}"
             else: # If it's supplier_name or already has po.
                 query_str += f" ORDER BY {sort_by.strip()}"
        else:
            print(f"WARNING [purchase_order_service.list_pos]: Invalid sort_by parameter '{sort_by}' ignored. Defaulting sort.")
            query_str += default_sort
    else:
        query_str += default_sort
        
    return fetch_data(_engine, query_str, params)

@st.cache_data(ttl=60, show_spinner="Fetching Purchase Order details...")
def get_po_by_id(_engine: Engine, po_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetches a specific Purchase Order by its ID, including its line items.
    Args:
        _engine: SQLAlchemy database engine instance.
        po_id: The ID of the Purchase Order.
    Returns:
        Dictionary of PO details with items, or None if not found.
    """
    if _engine is None or not po_id:
        print("ERROR [purchase_order_service.get_po_by_id]: Database engine or PO ID not provided.")
        return None
        
    po_header_query = text("""
        SELECT po.po_id, po.po_number, po.supplier_id, s.name as supplier_name,
               po.order_date, po.expected_delivery_date, po.status,
               po.total_amount, po.notes, po.created_by_user_id,
               po.created_at, po.updated_at
        FROM purchase_orders po JOIN suppliers s ON po.supplier_id = s.supplier_id
        WHERE po.po_id = :po_id;
    """)
    po_items_query = text("""
        SELECT poi.po_item_id, poi.item_id, i.name as item_name, i.unit as item_unit,
               poi.quantity_ordered, poi.unit_price, poi.line_total
        FROM purchase_order_items poi JOIN items i ON poi.item_id = i.item_id
        WHERE poi.po_id = :po_id ORDER BY i.name;
    """)
    try:
        with _engine.connect() as connection:
            header_result = connection.execute(po_header_query, {"po_id": po_id}).mappings().first()
            if not header_result: 
                print(f"WARNING [purchase_order_service.get_po_by_id]: No PO found for ID {po_id}.")
                return None
            po_header = dict(header_result)
            items_result = connection.execute(po_items_query, {"po_id": po_id}).mappings().all()
            po_header["items"] = [dict(item) for item in items_result]
            return po_header
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR [purchase_order_service.get_po_by_id]: Database error fetching PO details for po_id {po_id}: {e}\n{traceback.format_exc()}")
        return None

def create_po(engine: Engine, po_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Tuple[bool, str, Optional[int]]:
    """
    Creates a new Purchase Order and its line items.
    Args:
        engine: SQLAlchemy database engine instance.
        po_data: Dictionary of PO header details.
        items_data: List of dictionaries for PO line items.
    Returns:
        Tuple (success_status, message, new_po_id).
    """
    if engine is None: return False, "Database engine not available.", None
    
    required_header = ["supplier_id", "order_date", "created_by_user_id"]
    missing_fields = [f for f in required_header if not po_data.get(f) or (isinstance(po_data.get(f), str) and not str(po_data.get(f)).strip())]
    if missing_fields:
        return False, f"Missing or empty required PO header fields: {', '.join(missing_fields)}", None
        
    if not items_data: return False, "Purchase Order must contain at least one item.", None

    for i, item in enumerate(items_data):
        try:
            qty = float(item.get('quantity_ordered', 0))
            price = float(item.get('unit_price', 0)) # Price can be 0 for FOC items
            if not item.get('item_id') or qty <= 0 or price < 0: 
                return False, f"Invalid data in item row {i+1}: Check Item ID, Quantity (>0), or Price (>=0).", None
        except (ValueError, TypeError):
            return False, f"Invalid numeric data for quantity/price in item row {i+1}.", None
            
    new_po_number = generate_po_number(engine)
    if not new_po_number: return False, "Failed to generate PO Number.", None

    total_po_amount = 0.0
    processed_items_for_db: List[Dict[str, Any]] = [] 
    for item in items_data:
        qty = float(item['quantity_ordered'])
        price = float(item['unit_price'])
        line_total = round(qty * price, 2)
        total_po_amount += line_total
        processed_items_for_db.append({
            "item_id": item['item_id'], 
            "quantity_ordered": qty, 
            "unit_price": price, 
            "line_total": line_total
        })
    total_po_amount = round(total_po_amount, 2)

    header_query_obj = text("""INSERT INTO purchase_orders (po_number, supplier_id, order_date, expected_delivery_date, status, total_amount, notes, created_by_user_id, created_at, updated_at)
                             VALUES (:po_number, :supplier_id, :order_date, :expected_delivery_date, :status, :total_amount, :notes, :created_by_user_id, NOW(), NOW()) RETURNING po_id;""")
    items_query_obj = text("""INSERT INTO purchase_order_items (po_id, item_id, quantity_ordered, unit_price, line_total)
                             VALUES (:po_id, :item_id, :quantity_ordered, :unit_price, :line_total);""")
    
    header_params = {
        "po_number": new_po_number, 
        "supplier_id": po_data['supplier_id'], 
        "order_date": po_data['order_date'],
        "expected_delivery_date": po_data.get('expected_delivery_date'), # Optional
        "status": po_data.get('status', PO_STATUS_DRAFT),
        "total_amount": total_po_amount, 
        "notes": (po_data.get('notes', '').strip() or None), 
        "created_by_user_id": po_data['created_by_user_id'].strip() # Known to exist
    }
    
    new_po_id: Optional[int] = None
    try:
        with engine.connect() as conn:
            with conn.begin(): # Start transaction
                res = conn.execute(header_query_obj, header_params)
                new_po_id = res.scalar_one_or_none()
                if not new_po_id: 
                    raise Exception("Failed to retrieve po_id after PO header insertion.")
                
                item_params_list_for_db = [{"po_id": new_po_id, **item_data_dict} for item_data_dict in processed_items_for_db] 
                if item_params_list_for_db: # Only execute if there are items
                    conn.execute(items_query_obj, item_params_list_for_db)
                    
        list_pos.clear() # Clear cache
        return True, f"Purchase Order {new_po_number} created successfully with ID {new_po_id}.", new_po_id
    except IntegrityError as e:
        msg = "Database integrity error."
        if "purchase_orders_po_number_key" in str(e).lower(): 
            msg = f"PO Number '{new_po_number}' conflict. This might indicate a sequence issue or concurrency."
        elif "purchase_order_items_item_id_fkey" in str(e).lower(): 
            msg = "Invalid Item ID in PO items. Please ensure all items exist in the item master."
        elif "purchase_orders_supplier_id_fkey" in str(e).lower(): 
            msg = "Invalid Supplier ID for PO. Please ensure the supplier exists."
        print(f"ERROR [purchase_order_service.create_po]: {msg} Details: {e}\n{traceback.format_exc()}")
        return False, msg, None
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR [purchase_order_service.create_po]: DB error creating PO: {e}\n{traceback.format_exc()}")
        return False, "A database error occurred while creating the Purchase Order.", None

def update_po_status(engine: Engine, po_id: int, new_status: str, user_id: str) -> Tuple[bool, str]:
    """
    Updates the status of a Purchase Order.
    Args:
        engine: SQLAlchemy database engine instance.
        po_id: The ID of the PO to update.
        new_status: The new status string.
        user_id: User ID performing the update.
    Returns:
        Tuple (success_status, message).
    """
    if engine is None: return False, "Database engine not available."
    if not all([po_id, new_status, user_id, user_id.strip()]): 
        return False, "Missing or invalid parameters: po_id, new_status, or user_id."
    if new_status not in ALL_PO_STATUSES: 
        return False, f"Invalid status provided: '{new_status}'."
    
    # Potentially add logic here to check if status transition is valid based on current status if needed
    
    query_obj = text("UPDATE purchase_orders SET status = :status, updated_at = NOW(), updated_by_user_id = :user_id WHERE po_id = :po_id;")
    # Assuming updated_by_user_id column exists. If not, remove it from query.
    try:
        with engine.connect() as conn:
            with conn.begin(): 
                result = conn.execute(query_obj, {"status": new_status, "po_id": po_id, "user_id": user_id.strip()})
        if result.rowcount > 0:
            list_pos.clear()
            get_po_by_id.clear() 
            return True, f"PO ID {po_id} status updated to '{new_status}'."
        else:
            # Check if PO exists and if status is already the new_status
            existing_po_df = fetch_data(engine, "SELECT status FROM purchase_orders WHERE po_id = :po_id", {"po_id": po_id}) 
            if existing_po_df.empty: 
                return False, f"Update failed: PO ID {po_id} not found."
            current_db_status = existing_po_df.iloc[0]['status']
            if current_db_status == new_status: 
                return True, f"PO ID {po_id} status is already '{new_status}'. No change made." # Not an error
            return False, f"Failed to update PO status for ID {po_id}. Row not found or status unchanged for other reasons."
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR [purchase_order_service.update_po_status]: DB error updating PO status for {po_id}: {e}\n{traceback.format_exc()}")
        return False, "A database error occurred while updating PO status."

def update_po_details(engine: Engine, po_id: int, po_data: Dict[str, Any], items_data: List[Dict[str, Any]], user_id: str) -> Tuple[bool, str]:
    """
    Updates the details of a Purchase Order, including its line items.
    Only 'Draft' POs can be edited.
    Args:
        engine: SQLAlchemy database engine instance.
        po_id: ID of the PO to update.
        po_data: Dictionary of new header data.
        items_data: List of dictionaries for new line items.
        user_id: User ID performing the update.
    Returns:
        Tuple (success_status, message).
    """
    if engine is None: return False, "Database engine not available."
    if not po_id: return False, "PO ID is required for update."
    if not user_id or not user_id.strip(): return False, "User ID is required for update."
    
    current_po_details = get_po_by_id(engine, po_id) # Uses _engine due to caching
    if not current_po_details:
        return False, f"Purchase Order ID {po_id} not found."
    if current_po_details.get('status') != PO_STATUS_DRAFT:
        return False, f"Purchase Order {current_po_details.get('po_number')} is in '{current_po_details.get('status')}' status and cannot be edited."

    if not items_data: return False, "Purchase Order must contain at least one item."
    for i, item in enumerate(items_data): # Validation for new/updated items
        try:
            qty = float(item.get('quantity_ordered', 0))
            price = float(item.get('unit_price', 0)) # Price can be 0
            if not item.get('item_id') or qty <= 0 or price < 0:
                return False, f"Invalid data in updated item row {i+1}: Check Item ID, Quantity (>0), or Price (>=0)."
        except (ValueError, TypeError):
            return False, f"Invalid numeric data for quantity/price in updated item row {i+1}."

    new_total_po_amount = 0.0
    processed_update_items: List[Dict[str, Any]] = []
    for item in items_data:
        quantity = float(item['quantity_ordered'])
        price = float(item['unit_price'])
        line_total = round(quantity * price, 2)
        new_total_po_amount += line_total
        processed_update_items.append({
            "item_id": item['item_id'], 
            "quantity_ordered": quantity,
            "unit_price": price, 
            "line_total": line_total
        })
    new_total_po_amount = round(new_total_po_amount, 2)

    update_header_query_obj = text("""
        UPDATE purchase_orders SET
            supplier_id = :supplier_id, order_date = :order_date,
            expected_delivery_date = :expected_delivery_date, notes = :notes,
            total_amount = :total_amount, updated_at = NOW(), updated_by_user_id = :user_id 
        WHERE po_id = :po_id;
    """) 
    delete_items_query_obj = text("DELETE FROM purchase_order_items WHERE po_id = :po_id;")
    insert_item_query_obj = text("""
        INSERT INTO purchase_order_items
        (po_id, item_id, quantity_ordered, unit_price, line_total)
        VALUES (:po_id, :item_id, :quantity_ordered, :unit_price, :line_total);
    """)

    header_params_update = { 
        "po_id": po_id, 
        "supplier_id": po_data.get('supplier_id'), # Assuming validation for this happens in UI
        "order_date": po_data.get('order_date'),
        "expected_delivery_date": po_data.get('expected_delivery_date'), # Optional
        "notes": (po_data.get('notes', '').strip() or None), 
        "total_amount": new_total_po_amount,
        "user_id": user_id.strip() 
    }
    # Validate required header fields for update
    if not header_params_update["supplier_id"] or not header_params_update["order_date"]:
        return False, "Supplier ID and Order Date are required for PO update."

    try:
        with engine.connect() as connection:
            with connection.begin(): # Start transaction
                connection.execute(update_header_query_obj, header_params_update)
                connection.execute(delete_items_query_obj, {"po_id": po_id})
                
                if processed_update_items: # Only insert if there are items
                    item_params_list_for_update = [{"po_id": po_id, **item_data_dict} for item_data_dict in processed_update_items] 
                    connection.execute(insert_item_query_obj, item_params_list_for_update)
            
        list_pos.clear() # Clear relevant caches
        get_po_by_id.clear() 
        return True, f"Purchase Order {current_po_details.get('po_number')} (ID: {po_id}) updated successfully."
    except IntegrityError as ie:
        msg = "Database integrity error while updating PO."
        if "item_id_fkey" in str(ie).lower(): msg = "Invalid Item ID in updated items. Ensure all items exist."
        elif "supplier_id_fkey" in str(ie).lower(): msg = "Invalid Supplier ID in PO header. Ensure supplier exists."
        print(f"ERROR [purchase_order_service.update_po_details]: {msg} Details: {ie}\n{traceback.format_exc()}")
        return False, msg
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR [purchase_order_service.update_po_details]: DB error updating PO {po_id}: {e}\n{traceback.format_exc()}")
        return False, "A database error occurred while updating the Purchase Order."

# Potentially add a function for cancelling a PO
# def cancel_po(engine: Engine, po_id: int, user_id: str, reason: str) -> Tuple[bool, str]:
# ... implementation for cancelling PO, updating status to PO_STATUS_CANCELLED ...
# ... should also consider if any stock implications if items were partially received, though typically GRN handles stock ...