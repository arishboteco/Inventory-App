# app/services/purchase_order_service.py
import streamlit as st
import pandas as pd
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError # For more specific error handling

# Assuming your database_utils.py is in app/db/
from app.db.database_utils import fetch_data
# Import the new constants
try:
    from app.core.constants import (
        PO_STATUS_DRAFT, PO_STATUS_ORDERED, PO_STATUS_FULLY_RECEIVED,
        PO_STATUS_PARTIALLY_RECEIVED, PO_STATUS_CANCELLED, ALL_PO_STATUSES
    )
except ImportError: # Fallback if constants haven't been updated yet or for local testing
    print("Warning: Could not import PO status constants from app.core.constants. Using fallbacks.")
    PO_STATUS_DRAFT = "Draft"
    PO_STATUS_ORDERED = "Ordered"
    PO_STATUS_PARTIALLY_RECEIVED = "Partially Received"
    PO_STATUS_FULLY_RECEIVED = "Fully Received"
    PO_STATUS_CANCELLED = "Cancelled"
    ALL_PO_STATUSES = [PO_STATUS_DRAFT, PO_STATUS_ORDERED, PO_STATUS_PARTIALLY_RECEIVED, PO_STATUS_FULLY_RECEIVED, PO_STATUS_CANCELLED]


def generate_po_number(engine) -> Optional[str]:
    """
    Generates a new Purchase Order Number (PO Number) using the 'po_sequence'.
    Format: PO-XXXX (e.g., PO-0001, PO-0010, PO-0100, PO-1000)
    Args:
        engine: SQLAlchemy database engine instance.
    Returns:
        A string representing the new PO Number, or None if generation fails.
    """
    if engine is None:
        print("ERROR: Database engine not available for PO Number generation.")
        return None
    try:
        with engine.connect() as connection:
            # Ensure you've created 'po_sequence' in your database
            result = connection.execute(text("SELECT nextval('po_sequence');"))
            seq_num = result.scalar_one()
            # Formats the number to 4 digits with leading zeros
            return f"PO-{seq_num:04d}"
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR: Error generating PO Number: {e}")
        return None

@st.cache_data(ttl=300, show_spinner="Fetching Purchase Orders...")
def list_pos(_engine, filters: Optional[Dict[str, Any]] = None, sort_by: Optional[str] = None) -> pd.DataFrame:
    """
    Fetches a list of purchase orders, optionally filtered and sorted.
    Args:
        _engine: SQLAlchemy database engine instance.
        filters: A dictionary of filters (e.g., {"status": "Ordered", "supplier_id": 1}).
        sort_by: Column name to sort by (e.g., "order_date DESC").
    Returns:
        A Pandas DataFrame containing purchase orders.
    """
    if _engine is None:
        print("ERROR: Database engine not available for list_pos.")
        return pd.DataFrame()

    query_str = """
        SELECT
            po.po_id,
            po.po_number,
            po.supplier_id,
            s.name AS supplier_name, -- Joined from suppliers table
            po.order_date,
            po.expected_delivery_date,
            po.status,
            po.total_amount,
            po.created_by_user_id,
            po.created_at,
            po.updated_at,
            po.notes
        FROM purchase_orders po
        JOIN suppliers s ON po.supplier_id = s.supplier_id
        WHERE 1=1
    """
    params = {}

    if filters:
        if "status" in filters and filters["status"]:
            query_str += " AND po.status = :status"
            params["status"] = filters["status"]
        if "supplier_id" in filters and filters["supplier_id"]:
            query_str += " AND po.supplier_id = :supplier_id"
            params["supplier_id"] = filters["supplier_id"]
        if "po_number_ilike" in filters and filters["po_number_ilike"]:
            query_str += " AND po.po_number ILIKE :po_number_ilike" # Case-insensitive search
            params["po_number_ilike"] = f"%{filters['po_number_ilike']}%"
        # Add more filters as needed (e.g., date ranges)

    if sort_by:
        # Basic safety check for sort_by
        valid_sort_columns = ["po_id", "po_number", "supplier_name", "order_date", "expected_delivery_date", "status", "total_amount", "created_at", "updated_at"]
        sort_column_candidate = sort_by.split(" ")[0].lower() # Get column name, ignore ASC/DESC for validation
        if sort_column_candidate in valid_sort_columns:
             query_str += f" ORDER BY po.{sort_by}" # Use original sort_by which may include DESC/ASC
        else:
            print(f"Warning: Invalid sort_by parameter ignored: {sort_by}. Defaulting sort.")
            query_str += " ORDER BY po.order_date DESC, po.created_at DESC"
    else:
        query_str += " ORDER BY po.order_date DESC, po.created_at DESC"

    return fetch_data(_engine, query_str, params)

@st.cache_data(ttl=60, show_spinner="Fetching Purchase Order details...")
def get_po_by_id(_engine, po_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetches a single purchase order and its line items by PO ID.
    Args:
        _engine: SQLAlchemy database engine.
        po_id: The ID of the purchase order.
    Returns:
        A dictionary containing the PO header and a list of its items, or None if not found.
    """
    if _engine is None or not po_id:
        print("ERROR: Database engine or PO ID not provided for get_po_by_id.")
        return None

    po_header_query = text("""
        SELECT
            po.po_id, po.po_number, po.supplier_id, s.name as supplier_name,
            po.order_date, po.expected_delivery_date, po.status,
            po.total_amount, po.notes, po.created_by_user_id,
            po.created_at, po.updated_at
        FROM purchase_orders po
        JOIN suppliers s ON po.supplier_id = s.supplier_id
        WHERE po.po_id = :po_id;
    """)

    po_items_query = text("""
        SELECT
            poi.po_item_id, poi.item_id, i.name as item_name, i.unit as item_unit,
            poi.quantity_ordered, poi.unit_price, poi.line_total
        FROM purchase_order_items poi
        JOIN items i ON poi.item_id = i.item_id
        WHERE poi.po_id = :po_id
        ORDER BY i.name;
    """)

    try:
        with _engine.connect() as connection:
            header_result = connection.execute(po_header_query, {"po_id": po_id}).mappings().first()
            if not header_result:
                return None # PO not found

            po_header = dict(header_result)
            items_result = connection.execute(po_items_query, {"po_id": po_id}).mappings().all()
            po_header["items"] = [dict(item) for item in items_result]
            return po_header
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR: Database error fetching PO details for po_id {po_id}: {e}")
        return None

def create_po(engine, po_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Tuple[bool, str, Optional[int]]:
    """
    Creates a new Purchase Order and its items.
    Args:
        engine: SQLAlchemy database engine instance.
        po_data: Dictionary containing PO header details (supplier_id, order_date, etc.).
        items_data: List of dictionaries, each for an item (item_id, quantity_ordered, unit_price).
    Returns:
        Tuple (bool: success, str: message, Optional[int]: new_po_id).
    """
    if engine is None:
        return False, "Database engine not available.", None

    required_header_fields = ["supplier_id", "order_date", "created_by_user_id"]
    if not all(po_data.get(field) for field in required_header_fields):
        missing = [field for field in required_header_fields if not po_data.get(field)]
        return False, f"Missing required PO header fields: {', '.join(missing)}", None

    if not items_data:
        return False, "Purchase Order must contain at least one item.", None

    for i, item in enumerate(items_data):
        if not item.get('item_id') or \
           item.get('quantity_ordered') is None or float(item.get('quantity_ordered', 0)) <= 0 or \
           item.get('unit_price') is None or float(item.get('unit_price', 0)) < 0: # Price can be 0
            return False, f"Invalid data in item row {i+1}: Missing item_id, or invalid quantity/price.", None

    # Generate PO Number
    new_po_number = generate_po_number(engine)
    if not new_po_number:
        return False, "Failed to generate PO Number.", None

    # Calculate totals
    total_po_amount = 0.0
    processed_items_data = []
    for item in items_data:
        try:
            quantity = float(item['quantity_ordered'])
            price = float(item['unit_price'])
        except (ValueError, TypeError) as e:
            return False, f"Invalid numeric value for quantity or price in item data: {item}. Error: {e}", None

        line_total = round(quantity * price, 2)
        total_po_amount += line_total
        processed_items_data.append({
            "item_id": item['item_id'],
            "quantity_ordered": quantity,
            "unit_price": price,
            "line_total": line_total
        })
    total_po_amount = round(total_po_amount, 2)

    header_query = text("""
        INSERT INTO purchase_orders
        (po_number, supplier_id, order_date, expected_delivery_date, status,
        total_amount, notes, created_by_user_id, created_at, updated_at)
        VALUES
        (:po_number, :supplier_id, :order_date, :expected_delivery_date, :status,
        :total_amount, :notes, :created_by_user_id, NOW(), NOW())
        RETURNING po_id;
    """)
    items_query_str = """
        INSERT INTO purchase_order_items
        (po_id, item_id, quantity_ordered, unit_price, line_total)
        VALUES (:po_id, :item_id, :quantity_ordered, :unit_price, :line_total);
    """

    header_params = {
        "po_number": new_po_number,
        "supplier_id": po_data['supplier_id'],
        "order_date": po_data['order_date'],
        "expected_delivery_date": po_data.get('expected_delivery_date'),
        "status": po_data.get('status', PO_STATUS_DRAFT),
        "total_amount": total_po_amount,
        "notes": (po_data.get('notes', '').strip() or None),
        "created_by_user_id": po_data['created_by_user_id']
    }

    try:
        with engine.connect() as connection:
            with connection.begin(): # Start transaction
                result = connection.execute(header_query, header_params)
                new_po_id = result.scalar_one_or_none()

                if not new_po_id:
                    raise Exception("Failed to retrieve po_id after PO header insertion.")

                item_params_list = []
                for item in processed_items_data:
                    item_params_list.append({
                        "po_id": new_po_id,
                        "item_id": item['item_id'],
                        "quantity_ordered": item['quantity_ordered'],
                        "unit_price": item['unit_price'],
                        "line_total": item['line_total']
                    })
                
                if item_params_list:
                    connection.execute(text(items_query_str), item_params_list)
            # Transaction commits here if no exceptions

        list_pos.clear()
        return True, f"Purchase Order {new_po_number} created successfully with ID {new_po_id}.", new_po_id
    except IntegrityError as e:
        error_msg = "Database integrity error creating Purchase Order."
        if "purchase_orders_po_number_key" in str(e).lower():
             error_msg = f"Failed to create PO: PO Number '{new_po_number}' conflict. This might indicate a sequence issue or race condition."
        elif "purchase_order_items_item_id_fkey" in str(e).lower():
            error_msg = "Failed to create PO: One or more selected Item IDs are invalid."
        elif "purchase_orders_supplier_id_fkey" in str(e).lower():
            error_msg = "Failed to create PO: The selected Supplier ID is invalid."
        print(f"ERROR: {error_msg} Details: {e}")
        return False, error_msg, None
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR: Database error creating Purchase Order: {e}")
        return False, "A database error occurred while creating the Purchase Order.", None

def update_po_status(engine, po_id: int, new_status: str, user_id: str) -> Tuple[bool, str]:
    """
    Updates the status of a Purchase Order.
    Args:
        engine: SQLAlchemy database engine instance.
        po_id: The ID of the PO to update.
        new_status: The new status to set.
        user_id: The ID of the user making the change. (Currently not used in DB query but good for audit logs if added)
    Returns:
        Tuple (bool: success, str: message).
    """
    if engine is None: return False, "Database engine not available."
    if not po_id or not new_status:
        return False, "Missing po_id or new_status."

    if new_status not in ALL_PO_STATUSES: # Validate status
        return False, f"Invalid status: {new_status}. Allowed statuses are: {', '.join(ALL_PO_STATUSES)}"

    query = text("""
        UPDATE purchase_orders
        SET status = :status, updated_at = NOW()
        WHERE po_id = :po_id;
    """)

    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, {"status": new_status, "po_id": po_id})

        if result.rowcount > 0:
            list_pos.clear()
            get_po_by_id.clear() # Corrected
            return True, f"Purchase Order ID {po_id} status updated to '{new_status}'."
        else:
            # Check if PO exists to give a more specific message
            existing_po_check_df = fetch_data(engine, "SELECT status FROM purchase_orders WHERE po_id = :po_id", {"po_id": po_id})
            if existing_po_check_df.empty:
                return False, f"Purchase Order ID {po_id} not found."
            elif existing_po_check_df.iloc[0]['status'] == new_status:
                return False, f"Purchase Order ID {po_id} status is already '{new_status}'."
            else:
                return False, f"Failed to update status for Purchase Order ID {po_id} (unknown reason, rowcount 0)."
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR: Database error updating PO status for po_id {po_id}: {e}")
        return False, "A database error occurred while updating PO status."

# Placeholder for more advanced PO update function (e.g., editing a draft PO)
# def update_po_details(engine, po_id: int, po_data: Dict[str, Any], items_data: List[Dict[str, Any]], user_id: str) -> Tuple[bool, str]:
#     # This would be more complex:
#     # 1. Check if PO is in 'Draft' status.
#     # 2. Update header fields in 'purchase_orders'.
#     # 3. Delete existing items from 'purchase_order_items' for this po_id.
#     # 4. Re-insert new items_data.
#     # 5. Recalculate total_amount.
#     # 6. All within a transaction.
#     # 7. Clear caches.
#     pass