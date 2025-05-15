# app/services/purchase_order_service.py
import streamlit as st
import pandas as pd
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime
import traceback # For detailed error logging

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError 

from app.db.database_utils import fetch_data
try:
    from app.core.constants import (
        PO_STATUS_DRAFT, PO_STATUS_ORDERED, PO_STATUS_FULLY_RECEIVED,
        PO_STATUS_PARTIALLY_RECEIVED, PO_STATUS_CANCELLED, ALL_PO_STATUSES
    )
except ImportError: 
    print("Warning: Could not import PO status constants from app.core.constants. Using fallbacks in purchase_order_service.")
    PO_STATUS_DRAFT = "Draft"; PO_STATUS_ORDERED = "Ordered"
    PO_STATUS_PARTIALLY_RECEIVED = "Partially Received"; PO_STATUS_FULLY_RECEIVED = "Fully Received"
    PO_STATUS_CANCELLED = "Cancelled"
    ALL_PO_STATUSES = [PO_STATUS_DRAFT, PO_STATUS_ORDERED, PO_STATUS_PARTIALLY_RECEIVED, PO_STATUS_FULLY_RECEIVED, PO_STATUS_CANCELLED]


def generate_po_number(engine) -> Optional[str]:
    if engine is None:
        print("ERROR (PO Service): Database engine not available for PO Number generation.")
        return None
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT nextval('po_sequence');"))
            seq_num = result.scalar_one()
            return f"PO-{seq_num:04d}" # Assumes 4-digit padding, adjust if needed
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR (PO Service): Error generating PO Number: {e}")
        return None

@st.cache_data(ttl=300, show_spinner="Fetching Purchase Orders...")
def list_pos(_engine, filters: Optional[Dict[str, Any]] = None, sort_by: Optional[str] = None) -> pd.DataFrame:
    if _engine is None:
        print("ERROR (PO Service): Database engine not available for list_pos.")
        return pd.DataFrame()
    query_str = """
        SELECT po.po_id, po.po_number, po.supplier_id, s.name AS supplier_name, 
               po.order_date, po.expected_delivery_date, po.status, po.total_amount, 
               po.created_by_user_id, po.created_at, po.updated_at, po.notes
        FROM purchase_orders po
        JOIN suppliers s ON po.supplier_id = s.supplier_id
        WHERE 1=1
    """
    params = {}
    if filters:
        if "status" in filters and filters["status"]:
            query_str += " AND po.status = :status"; params["status"] = filters["status"]
        if "supplier_id" in filters and filters["supplier_id"]:
            query_str += " AND po.supplier_id = :supplier_id"; params["supplier_id"] = filters["supplier_id"]
        if "po_number_ilike" in filters and filters["po_number_ilike"]:
            query_str += " AND po.po_number ILIKE :po_number_ilike"; params["po_number_ilike"] = f"%{filters['po_number_ilike']}%"
    
    valid_sort_cols = ["po_id", "po_number", "supplier_name", "order_date", "expected_delivery_date", "status", "total_amount", "created_at", "updated_at"]
    default_sort = " ORDER BY po.order_date DESC, po.created_at DESC"
    if sort_by:
        sort_col_candidate = sort_by.split(" ")[0].lower().replace("po.", "") 
        if sort_col_candidate in valid_sort_cols:
             query_str += f" ORDER BY po.{sort_by}" # Use original sort_by as it might contain ASC/DESC
        else:
            print(f"Warning (PO Service): Invalid sort_by parameter ignored: {sort_by}. Defaulting sort.")
            query_str += default_sort
    else:
        query_str += default_sort
    return fetch_data(_engine, query_str, params)

@st.cache_data(ttl=60, show_spinner="Fetching Purchase Order details...")
def get_po_by_id(_engine, po_id: int) -> Optional[Dict[str, Any]]:
    if _engine is None or not po_id:
        print("ERROR (PO Service): Database engine or PO ID not provided for get_po_by_id.")
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
            if not header_result: return None
            po_header = dict(header_result)
            items_result = connection.execute(po_items_query, {"po_id": po_id}).mappings().all()
            po_header["items"] = [dict(item) for item in items_result]
            return po_header
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR (PO Service): Database error fetching PO details for po_id {po_id}: {e}")
        return None

def create_po(engine, po_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Tuple[bool, str, Optional[int]]:
    if engine is None: return False, "Database engine not available.", None
    required_header = ["supplier_id", "order_date", "created_by_user_id"]
    if not all(po_data.get(f) for f in required_header):
        return False, f"Missing required PO header fields: {', '.join(f for f in required_header if not po_data.get(f))}", None
    if not items_data: return False, "Purchase Order must contain at least one item.", None

    for i, item in enumerate(items_data):
        try:
            qty = float(item.get('quantity_ordered', 0))
            price = float(item.get('unit_price', 0))
            if not item.get('item_id') or qty <= 0 or price < 0: # Price can be 0 for free items
                return False, f"Invalid data in item row {i+1}: Check Item, Quantity (>0), or Price (>=0).", None
        except (ValueError, TypeError):
            return False, f"Invalid numeric data for quantity/price in item row {i+1}.", None
            
    new_po_number = generate_po_number(engine)
    if not new_po_number: return False, "Failed to generate PO Number.", None

    total_po_amount = 0.0; processed_items_for_db = [] # Renamed variable
    for item in items_data:
        qty = float(item['quantity_ordered']); price = float(item['unit_price'])
        line_total = round(qty * price, 2); total_po_amount += line_total
        processed_items_for_db.append({"item_id": item['item_id'], "quantity_ordered": qty, "unit_price": price, "line_total": line_total})
    total_po_amount = round(total_po_amount, 2)

    # Use TextClause objects for direct execution
    header_query_obj = text("""INSERT INTO purchase_orders (po_number, supplier_id, order_date, expected_delivery_date, status, total_amount, notes, created_by_user_id, created_at, updated_at)
                             VALUES (:po_number, :supplier_id, :order_date, :expected_delivery_date, :status, :total_amount, :notes, :created_by_user_id, NOW(), NOW()) RETURNING po_id;""")
    items_query_obj = text("""INSERT INTO purchase_order_items (po_id, item_id, quantity_ordered, unit_price, line_total)
                             VALUES (:po_id, :item_id, :quantity_ordered, :unit_price, :line_total);""")
    
    header_params = {"po_number": new_po_number, "supplier_id": po_data['supplier_id'], "order_date": po_data['order_date'],
                     "expected_delivery_date": po_data.get('expected_delivery_date'), "status": po_data.get('status', PO_STATUS_DRAFT),
                     "total_amount": total_po_amount, "notes": (po_data.get('notes', '').strip() or None), 
                     "created_by_user_id": po_data['created_by_user_id']}
    try:
        with engine.connect() as conn:
            with conn.begin():
                res = conn.execute(header_query_obj, header_params); new_po_id = res.scalar_one_or_none()
                if not new_po_id: raise Exception("Failed to retrieve po_id after PO header insertion.")
                item_params_list_for_db = [{"po_id": new_po_id, **item_data_dict} for item_data_dict in processed_items_for_db] 
                if item_params_list_for_db: conn.execute(items_query_obj, item_params_list_for_db)
        list_pos.clear(); return True, f"Purchase Order {new_po_number} created successfully with ID {new_po_id}.", new_po_id
    except IntegrityError as e:
        msg = "DB integrity error."
        if "purchase_orders_po_number_key" in str(e).lower(): msg = f"PO Number '{new_po_number}' conflict."
        elif "purchase_order_items_item_id_fkey" in str(e).lower(): msg = "Invalid Item ID in PO items." # Check constraint name
        elif "purchase_orders_supplier_id_fkey" in str(e).lower(): msg = "Invalid Supplier ID for PO." # Check constraint name
        print(f"ERROR (PO Service): {msg} Details: {e}"); return False, msg, None
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR (PO Service): DB error creating PO: {e}"); return False, "A DB error occurred while creating PO.", None

def update_po_status(engine, po_id: int, new_status: str, user_id: str) -> Tuple[bool, str]:
    if engine is None: return False, "Database engine not available."
    if not all([po_id, new_status, user_id]): return False, "Missing po_id, new_status, or user_id."
    if new_status not in ALL_PO_STATUSES: return False, f"Invalid status: {new_status}."
    
    query_obj = text("UPDATE purchase_orders SET status = :status, updated_at = NOW() WHERE po_id = :po_id;")
    try:
        with engine.connect() as conn:
            with conn.begin(): result = conn.execute(query_obj, {"status": new_status, "po_id": po_id})
        if result.rowcount > 0:
            list_pos.clear(); get_po_by_id.clear(); return True, f"PO ID {po_id} status updated to '{new_status}'."
        else:
            existing_po = fetch_data(engine, "SELECT status FROM purchase_orders WHERE po_id = :po_id", {"po_id": po_id}) # Changed var name
            if existing_po.empty: return False, f"PO ID {po_id} not found."
            if existing_po.iloc[0]['status'] == new_status: return False, f"PO ID {po_id} status already '{new_status}'."
            return False, f"Failed to update PO status for ID {po_id} (unknown reason)."
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR (PO Service): DB error updating PO status for {po_id}: {e}"); return False, "A DB error occurred."

def update_po_details(engine, po_id: int, po_data: Dict[str, Any], items_data: List[Dict[str, Any]], user_id: str) -> Tuple[bool, str]:
    if engine is None: return False, "Database engine not available."
    if not po_id: return False, "PO ID is required for update."
    
    print(f"DEBUG (update_po_details): Starting update for PO ID: {po_id}")
    print(f"DEBUG (update_po_details): Received po_data: {po_data}")
    print(f"DEBUG (update_po_details): Received items_data: {items_data}")

    current_po_details = get_po_by_id(engine, po_id) 
    if not current_po_details:
        return False, f"Purchase Order ID {po_id} not found."
    if current_po_details.get('status') != PO_STATUS_DRAFT:
        return False, f"Purchase Order {current_po_details.get('po_number')} is in '{current_po_details.get('status')}' status and cannot be edited."

    if not items_data: return False, "Purchase Order must contain at least one item."
    for i, item in enumerate(items_data):
        try:
            qty = float(item.get('quantity_ordered', 0))
            price = float(item.get('unit_price', 0))
            if not item.get('item_id') or qty <= 0 or price < 0:
                return False, f"Invalid data in updated item row {i+1}: Check Item, Quantity (>0), or Price (>=0)."
        except (ValueError, TypeError):
            return False, f"Invalid numeric data for quantity/price in updated item row {i+1}."

    new_total_po_amount = 0.0
    processed_update_items = []
    for item in items_data:
        quantity = float(item['quantity_ordered'])
        price = float(item['unit_price'])
        line_total = round(quantity * price, 2)
        new_total_po_amount += line_total
        processed_update_items.append({
            "item_id": item['item_id'], "quantity_ordered": quantity,
            "unit_price": price, "line_total": line_total
        })
    new_total_po_amount = round(new_total_po_amount, 2)
    print(f"DEBUG (update_po_details): Calculated new_total_po_amount: {new_total_po_amount}")

    update_header_query_obj = text("""
        UPDATE purchase_orders SET
            supplier_id = :supplier_id, order_date = :order_date,
            expected_delivery_date = :expected_delivery_date, notes = :notes,
            total_amount = :total_amount, updated_at = NOW() 
        WHERE po_id = :po_id;
    """) # user_id for updated_by can be added if schema supports
    delete_items_query_obj = text("DELETE FROM purchase_order_items WHERE po_id = :po_id;")
    insert_item_query_obj = text("""
        INSERT INTO purchase_order_items
        (po_id, item_id, quantity_ordered, unit_price, line_total)
        VALUES (:po_id, :item_id, :quantity_ordered, :unit_price, :line_total);
    """)

    header_params_update = { # Renamed var
        "po_id": po_id, "supplier_id": po_data['supplier_id'], 
        "order_date": po_data['order_date'],
        "expected_delivery_date": po_data.get('expected_delivery_date'),
        "notes": (po_data.get('notes', '').strip() or None), 
        "total_amount": new_total_po_amount,
    }
    print(f"DEBUG (update_po_details): Header params for update: {header_params_update}")

    try:
        with engine.connect() as connection:
            with connection.begin(): 
                print(f"DEBUG (update_po_details): Updating PO Header for po_id: {po_id}")
                connection.execute(update_header_query_obj, header_params_update)
                print(f"DEBUG (update_po_details): PO Header updated. Deleting old items for po_id: {po_id}")
                connection.execute(delete_items_query_obj, {"po_id": po_id})
                print(f"DEBUG (update_po_details): Old items deleted. Inserting new items for po_id: {po_id}")
                
                if processed_update_items:
                    item_params_list_for_update = [{"po_id": po_id, **item_data_dict} for item_data_dict in processed_update_items] # Renamed var
                    print(f"DEBUG (update_po_details): New item params list: {item_params_list_for_update}")
                    connection.execute(insert_item_query_obj, item_params_list_for_update)
                    print(f"DEBUG (update_po_details): New items inserted.")
                else:
                    print(f"DEBUG (update_po_details): No items in processed_update_items to insert.")
            
        list_pos.clear()
        get_po_by_id.clear() 
        return True, f"Purchase Order {current_po_details.get('po_number')} (ID: {po_id}) updated successfully."
    except IntegrityError as ie:
        msg = "DB integrity error while updating PO."
        if "item_id_fkey" in str(ie).lower(): msg = "Invalid Item ID in updated items."
        elif "supplier_id_fkey" in str(ie).lower(): msg = "Invalid Supplier ID in PO header."
        print(f"ERROR (PO Service update_po_details): {msg} Details: {ie}\n{traceback.format_exc()}")
        return False, msg
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR (PO Service update_po_details): DB error updating PO {po_id}: {e}\n{traceback.format_exc()}")
        return False, "A DB error occurred while updating the PO."