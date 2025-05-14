# app/services/indent_service.py
import streamlit as st
import pandas as pd
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime, timedelta, date
import traceback 

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.database_utils import fetch_data
from app.core.constants import (
    STATUS_SUBMITTED,
    STATUS_PROCESSING,
    STATUS_COMPLETED, 
    STATUS_CANCELLED, # For overall indent status
    ITEM_STATUS_PENDING_ISSUE,
    ITEM_STATUS_FULLY_ISSUED,
    ITEM_STATUS_PARTIALLY_ISSUED,
    ITEM_STATUS_CANCELLED_ITEM, # Corrected constant name for individual items
    TX_INDENT_FULFILL 
)
# Import other services
from app.services import item_service 
from app.services import stock_service 

# ─────────────────────────────────────────────────────────
# INDENT FUNCTIONS
# ─────────────────────────────────────────────────────────
def generate_mrn(engine) -> Optional[str]:
    """
    Generates a new Material Request Number (MRN) using a database sequence.
    Example: MRN-YYYYMM-NNNNN
    Args:
        engine: SQLAlchemy database engine instance.
    Returns:
        A string representing the new MRN, or None if generation fails.
    """
    if engine is None:
        # UI calls like st.error are generally better in page scripts,
        # but if this is a critical unrecoverable state for a core function, it can be acceptable.
        # Consider returning a specific error message or raising an exception for the caller to handle.
        print("ERROR (indent_service): Database engine not available for MRN generation.")
        st.error("Database engine not available for MRN generation.") 
        return None
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT nextval('mrn_seq');"))
            seq_num = result.scalar_one()
            return f"MRN-{datetime.now().strftime('%Y%m')}-{seq_num:05d}"
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR (indent_service): Error generating MRN: {e}")
        st.error(f"Error generating MRN: Sequence 'mrn_seq' might not exist or other DB error. {e}")
        return None

def create_indent(engine, indent_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Creates a new indent (material request) and its associated items in the database.
    Args:
        engine: SQLAlchemy database engine instance.
        indent_data: Dictionary containing header details for the indent.
        items_data: List of dictionaries, each representing an item in the indent.
    Returns:
        A tuple (bool, str) indicating success status and a message.
    """
    if engine is None:
        return False, "Database engine not available."
    
    required_header_fields = ["mrn", "requested_by", "department", "date_required"]
    missing_or_empty_fields = [
        k for k in required_header_fields 
        if not indent_data.get(k) or (isinstance(indent_data.get(k), str) and not indent_data.get(k).strip())
    ]
    if missing_or_empty_fields:
        return False, f"Missing or empty required indent header fields: {', '.join(missing_or_empty_fields)}"
    
    if not items_data:
        return False, "Indent must contain at least one item."

    for i, item in enumerate(items_data):
        try:
            qty_val = float(item.get('requested_qty', 0))
            if not item.get('item_id') or qty_val <= 0:
                return False, f"Invalid data in item row {i+1}: Item ID missing or requested quantity is not positive. Data: {item}"
        except (ValueError, TypeError):
            return False, f"Invalid numeric quantity for item in row {i+1}. Data: {item}"


    indent_query_str = """
        INSERT INTO indents (mrn, requested_by, department, date_required, notes, status, date_submitted)
        VALUES (:mrn, :requested_by, :department, :date_required, :notes, :status, NOW())
        RETURNING indent_id;
    """
    item_query_str = """
        INSERT INTO indent_items (indent_id, item_id, requested_qty, notes, item_status)
        VALUES (:indent_id, :item_id, :requested_qty, :notes, :item_status);
    """
    
    notes_value = indent_data.get("notes")
    cleaned_notes = notes_value.strip() if isinstance(notes_value, str) else None
    if cleaned_notes == "": cleaned_notes = None # Ensure empty strings are stored as NULL
    
    indent_params = {
        "mrn": indent_data["mrn"].strip(),
        "requested_by": indent_data["requested_by"].strip(),
        "department": indent_data["department"],
        "date_required": indent_data["date_required"],
        "notes": cleaned_notes,
        "status": indent_data.get("status", STATUS_SUBMITTED)
    }

    try:
        with engine.connect() as connection:
            with connection.begin(): 
                result = connection.execute(text(indent_query_str), indent_params)
                new_indent_id = result.scalar_one_or_none()
                
                if not new_indent_id:
                    raise Exception("Failed to retrieve indent_id after indent header insertion.")
                
                item_params_list = [
                    {
                        "indent_id": new_indent_id,
                        "item_id": item['item_id'],
                        "requested_qty": float(item['requested_qty']),
                        "notes": (item.get('notes') or "").strip() or None, # Ensure notes are cleaned
                        "item_status": ITEM_STATUS_PENDING_ISSUE 
                    } for item in items_data
                ]
                connection.execute(text(item_query_str), item_params_list)
        
        # Clear caches for functions that list indents
        get_indents.clear() 
        get_indents_for_processing.clear() 
        return True, f"Indent {indent_data['mrn']} created successfully with ID {new_indent_id}."
    except IntegrityError as e:
        error_msg = "Database integrity error creating indent."
        if "indents_mrn_key" in str(e).lower() or ("unique constraint" in str(e).lower() and "mrn" in str(e).lower()):
            error_msg = f"Failed to create indent: MRN '{indent_params['mrn']}' already exists."
        elif "indent_items_item_id_fkey" in str(e).lower():
            error_msg = "Failed to create indent: One or more selected Item IDs are invalid or do not exist."
        # st.error(f"{error_msg} Details: {e}") # Avoid st.error in backend services
        print(f"ERROR (indent_service): {error_msg} Details: {e}")
        return False, error_msg.split('.')[0] # Return a cleaner message to UI
    except (SQLAlchemyError, Exception) as e:
        # st.error(f"Database error creating indent: {e}\n{traceback.format_exc()}")
        print(f"ERROR (indent_service): Database error creating indent: {e}\n{traceback.format_exc()}")
        return False, "A database error occurred while creating the indent."

@st.cache_data(ttl=120, show_spinner="Fetching indent list...")
def get_indents(
    _engine, mrn_filter: Optional[str] = None, dept_filter: Optional[str] = None,
    status_filter: Optional[str] = None, date_start_str: Optional[str] = None,
    date_end_str: Optional[str] = None
) -> pd.DataFrame:
    if _engine is None:
        return pd.DataFrame()
    
    date_start_filter, date_end_filter = None, None
    if date_start_str:
        try: date_start_filter = datetime.strptime(date_start_str, '%Y-%m-%d').date()
        except ValueError: print(f"Warning (indent_service): Invalid start date format: {date_start_str}. Ignoring.")
    if date_end_str:
        try: date_end_filter = datetime.strptime(date_end_str, '%Y-%m-%d').date()
        except ValueError: print(f"Warning (indent_service): Invalid end date format: {date_end_str}. Ignoring.")

    query_str = """
        SELECT 
            i.indent_id, i.mrn, i.requested_by, i.department, i.date_required,
            i.date_submitted, i.status, i.notes AS indent_notes, 
            COUNT(ii.indent_item_id) AS item_count
        FROM indents i 
        LEFT JOIN indent_items ii ON i.indent_id = ii.indent_id 
        WHERE 1=1
    """
    params = {}
    if mrn_filter: query_str += " AND i.mrn ILIKE :mrn"; params['mrn'] = f"%{mrn_filter}%"
    if dept_filter: query_str += " AND i.department = :department"; params['department'] = dept_filter
    if status_filter: query_str += " AND i.status = :status"; params['status'] = status_filter
    if date_start_filter: query_str += " AND DATE(i.date_submitted) >= :date_from"; params['date_from'] = date_start_filter
    if date_end_filter: query_str += " AND DATE(i.date_submitted) <= :date_to"; params['date_to'] = date_end_filter # Corrected from date_end_str
        
    query_str += """
        GROUP BY i.indent_id, i.mrn, i.requested_by, i.department, i.date_required,
                 i.date_submitted, i.status, i.notes
        ORDER BY i.date_submitted DESC, i.indent_id DESC;
    """
    df = fetch_data(_engine, query_str, params)
    if not df.empty:
        for col in ['date_required', 'date_submitted']:
             if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce')
        if 'item_count' in df.columns:
             df['item_count'] = pd.to_numeric(df['item_count'], errors='coerce').fillna(0).astype(int)
    return df

@st.cache_data(ttl=120, show_spinner="Fetching indents to process...")
def get_indents_for_processing(_engine) -> pd.DataFrame:
    if _engine is None:
        print("ERROR (indent_service): Database engine not available for get_indents_for_processing.")
        return pd.DataFrame()
    
    query_str = """
        SELECT i.indent_id, i.mrn, i.department, i.requested_by,
               i.date_submitted, i.date_required, i.status
        FROM indents i
        WHERE i.status IN (:status_submitted, :status_processing)
        ORDER BY i.date_submitted ASC, i.mrn ASC;
    """
    params = {"status_submitted": STATUS_SUBMITTED, "status_processing": STATUS_PROCESSING}
    df = fetch_data(_engine, query_str, params)
    if not df.empty:
        for col in ['date_required', 'date_submitted']:
            if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

def get_indent_items_for_display(_engine, indent_id: int) -> pd.DataFrame:
    if _engine is None or not indent_id:
        print("ERROR (indent_service): DB engine or indent_id missing for get_indent_items_for_display.")
        return pd.DataFrame()

    query_str = """
        SELECT ii.indent_item_id, ii.item_id, i.name AS item_name, i.unit AS item_unit,
               i.current_stock AS stock_on_hand, ii.requested_qty,
               ii.issued_qty, ii.item_status, ii.notes AS item_notes
        FROM indent_items ii
        JOIN items i ON ii.item_id = i.item_id
        WHERE ii.indent_id = :indent_id
        ORDER BY i.name ASC;
    """
    params = {"indent_id": indent_id}
    df = fetch_data(_engine, query_str, params)
    
    if not df.empty:
        for col in ['requested_qty', 'issued_qty', 'stock_on_hand']:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df['qty_remaining_to_issue'] = (df['requested_qty'] - df['issued_qty']).clip(lower=0)
        
        if 'item_status' in df.columns:
             df['item_status'] = df['item_status'].fillna(ITEM_STATUS_PENDING_ISSUE)
    else: 
        df = pd.DataFrame(columns=[
            'indent_item_id', 'item_id', 'item_name', 'item_unit', 
            'stock_on_hand', 'requested_qty', 'issued_qty', 
            'item_status', 'item_notes', 'qty_remaining_to_issue'
        ])
    return df

def get_indent_details_for_pdf(engine, mrn: str) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
    if engine is None or not mrn:
        print("ERROR (indent_service): Database engine or MRN not provided for PDF details.")
        return None, None
    
    header_data = None
    items_data = None
    try:
        with engine.connect() as connection:
            header_query = text("""
                SELECT ind.indent_id, ind.mrn, ind.department, ind.requested_by,
                       ind.date_submitted, ind.date_required, ind.status, ind.notes
                FROM indents ind WHERE ind.mrn = :mrn;
            """)
            header_result = connection.execute(header_query, {"mrn": mrn}).mappings().first()
            
            if not header_result:
                print(f"Warning (indent_service): Indent with MRN '{mrn}' not found for PDF generation.")
                return None, None
            
            header_data = dict(header_result)
            if header_data.get('date_submitted'):
                header_data['date_submitted'] = pd.to_datetime(header_data['date_submitted']).strftime('%Y-%m-%d %H:%M')
            if header_data.get('date_required'):
                 header_data['date_required'] = pd.to_datetime(header_data['date_required']).strftime('%Y-%m-%d')

            items_query = text("""
                SELECT ii.item_id, i.name AS item_name, i.unit AS item_unit,
                       COALESCE(i.category, 'Uncategorized') AS item_category,
                       COALESCE(i.sub_category, 'General') AS item_sub_category,
                       ii.requested_qty, ii.notes AS item_notes
                FROM indent_items ii
                JOIN items i ON ii.item_id = i.item_id
                JOIN indents ind ON ii.indent_id = ind.indent_id
                WHERE ind.mrn = :mrn
                ORDER BY item_category ASC, item_sub_category ASC, item_name ASC;
            """)
            items_result = connection.execute(items_query, {"mrn": mrn}).mappings().all()
            items_data = [dict(row) for row in items_result]
        
        return header_data, items_data
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR (indent_service): Database error fetching details for indent PDF (MRN: {mrn}): {e}\n{traceback.format_exc()}")
        return None, None

def _update_indent_overall_status(connection, indent_id: int, new_status: str, user_id: str) -> None:
    update_indent_query = text("""
        UPDATE indents 
        SET status = :status, processed_by_user_id = :user_id, date_processed = NOW()
        WHERE indent_id = :indent_id;
    """)
    connection.execute(update_indent_query, {
        "status": new_status, "user_id": user_id, "indent_id": indent_id
    })

def process_indent_issuance(_engine, indent_id: int, items_to_issue: List[Dict], user_id: str, indent_mrn: str) -> Tuple[bool, str]:
    if _engine is None: return False, "Database engine not available."
    if not all([indent_id, items_to_issue is not None, user_id, indent_mrn]):
        return False, "Missing required parameters: indent_id, items_to_issue, user_id, or indent_mrn."

    processed_messages = []
    any_actual_issuance_occurred = False 

    try:
        with _engine.connect() as connection:
            with connection.begin(): 
                for item_data in items_to_issue:
                    indent_item_id = item_data.get('indent_item_id')
                    item_id = item_data.get('item_id')
                    qty_to_issue_now = 0.0 # Default
                    try:
                        qty_to_issue_now = float(item_data.get('qty_to_issue_now', 0))
                    except (ValueError, TypeError):
                        processed_messages.append(f"Skipped item ID {item_id}: Invalid quantity '{item_data.get('qty_to_issue_now')}'.")
                        continue
                    if qty_to_issue_now <= 0: continue # Skip if no quantity to issue for this item in this batch
                    
                    any_actual_issuance_occurred = True # Mark that we are attempting at least one issuance

                    # Lock the indent item row for update
                    current_item_details_query = text("SELECT requested_qty, issued_qty FROM indent_items WHERE indent_item_id = :indent_item_id FOR UPDATE;")
                    current_item_res = connection.execute(current_item_details_query, {"indent_item_id": indent_item_id}).mappings().first()
                    if not current_item_res:
                        raise Exception(f"Indent item ID {indent_item_id} (for item ID {item_id}) not found.")
                    
                    current_requested_qty = float(current_item_res['requested_qty'])
                    current_issued_qty = float(current_item_res['issued_qty'])
                    qty_still_pending = current_requested_qty - current_issued_qty

                    if qty_still_pending <= 0:
                        processed_messages.append(f"Item ID {item_id}: Already fulfilled or over-issued. No further issuance against this request line.")
                        continue # Skip this item as it's already fulfilled or over-issued.

                    original_qty_to_issue_now_for_msg = qty_to_issue_now # Store for messages
                    if qty_to_issue_now > qty_still_pending:
                        qty_to_issue_now = qty_still_pending
                        processed_messages.append(f"Item ID {item_id}: Issue qty ({original_qty_to_issue_now_for_msg:.2f}) reduced to pending amount ({qty_to_issue_now:.2f}).")

                    # Lock the item master row for stock update
                    stock_on_hand_query = text("SELECT current_stock FROM items WHERE item_id = :item_id FOR UPDATE;")
                    stock_on_hand_res = connection.execute(stock_on_hand_query, {"item_id": item_id}).scalar_one_or_none()
                    if stock_on_hand_res is None:
                        raise Exception(f"Item ID {item_id} not found in items master for stock check.")
                    stock_on_hand = float(stock_on_hand_res)

                    if qty_to_issue_now > stock_on_hand:
                        qty_to_issue_now = stock_on_hand # Clamp to available stock
                        processed_messages.append(f"Item ID {item_id}: Issue qty ({original_qty_to_issue_now_for_msg:.2f}) reduced to stock on hand ({qty_to_issue_now:.2f}).")

                    if qty_to_issue_now <= 0: # If clamping made it zero or less
                        processed_messages.append(f"Item ID {item_id}: Skipped (no available stock or quantity became zero after clamping).")
                        continue # Skip if no actual quantity can be issued
                    
                    # Call stock_service.record_stock_transaction (which now handles its own sub-transaction if no connection passed, or participates if connection is passed)
                    stock_tx_success = stock_service.record_stock_transaction(
                        item_id=item_id, 
                        quantity_change=-qty_to_issue_now, # Negative for issuance
                        transaction_type=TX_INDENT_FULFILL,
                        user_id=user_id, 
                        related_mrn=indent_mrn,
                        db_engine_param=None, # Explicitly pass None for engine
                        db_connection_param=connection # Pass the active connection
                    )
                    if not stock_tx_success:
                        # This exception will cause the main transaction to roll back
                        raise Exception(f"Failed to record stock transaction for item_id {item_id} on MRN {indent_mrn}.")

                    new_total_issued_for_item = current_issued_qty + qty_to_issue_now
                    new_item_status_for_item = ITEM_STATUS_PARTIALLY_ISSUED # Default
                    if new_total_issued_for_item >= current_requested_qty:
                        new_item_status_for_item = ITEM_STATUS_FULLY_ISSUED
                        new_total_issued_for_item = current_requested_qty # Clamp to requested qty to avoid over-issuance in records

                    update_indent_item_query = text("""
                        UPDATE indent_items 
                        SET issued_qty = :issued_qty, item_status = :item_status 
                        WHERE indent_item_id = :indent_item_id;
                    """)
                    connection.execute(update_indent_item_query, {
                        "issued_qty": new_total_issued_for_item,
                        "item_status": new_item_status_for_item,
                        "indent_item_id": indent_item_id
                    })
                    processed_messages.append(f"Item ID {item_id}: Issued {qty_to_issue_now:.2f}. New total issued: {new_total_issued_for_item:.2f}. Status: {new_item_status_for_item}.")

                # After processing all items, determine overall indent status
                all_items_statuses_query = text("SELECT item_status FROM indent_items WHERE indent_id = :indent_id;")
                item_statuses_results = connection.execute(all_items_statuses_query, {"indent_id": indent_id}).fetchall()
                
                all_statuses_list = [row[0] for row in item_statuses_results] if item_statuses_results else []
                current_overall_indent_status = STATUS_PROCESSING # Default for ongoing

                if not all_statuses_list: 
                    current_overall_indent_status = STATUS_SUBMITTED # Should not happen if items were processed
                # If all items are either fully issued or cancelled
                elif all(s == ITEM_STATUS_FULLY_ISSUED or s == ITEM_STATUS_CANCELLED_ITEM for s in all_statuses_list):
                    current_overall_indent_status = STATUS_COMPLETED
                # If no items are pending or partially issued, but some might be fully issued / cancelled item
                elif not any(s == ITEM_STATUS_PENDING_ISSUE or s == ITEM_STATUS_PARTIALLY_ISSUED for s in all_statuses_list):
                    current_overall_indent_status = STATUS_COMPLETED
                
                # Only update overall status if something was actually issued or if the status is changing to Completed
                if any_actual_issuance_occurred or current_overall_indent_status == STATUS_COMPLETED:
                    _update_indent_overall_status(connection, indent_id, current_overall_indent_status, user_id)
                    processed_messages.append(f"Indent MRN {indent_mrn} overall status updated to: {current_overall_indent_status}.")
                elif not items_to_issue: # No items were in the input list (e.g., user submitted empty form)
                     processed_messages.append(f"No items were specified for issuance in MRN {indent_mrn}.")
                # else: # Items were specified, but no actual stock was issued (e.g., all clamped to 0)
                #     processed_messages.append(f"No actual stock was issued for MRN {indent_mrn} in this batch, status remains.")


            # Clear caches after successful transaction
            item_service.get_all_items_with_stock.clear() 
            stock_service.get_stock_transactions.clear() 
            get_indents.clear()
            get_indents_for_processing.clear()
            
            final_message = "Indent processing complete."
            if processed_messages:
                final_message += " Details: " + " | ".join(processed_messages)
            return True, final_message

    except Exception as e:
        # st.error(f"Error during indent processing for MRN {indent_mrn}: {e}") # Avoid st.error in backend
        print(f"ERROR (indent_service): Exception during indent processing for MRN {indent_mrn}:\n{traceback.format_exc()}")
        detailed_error_message = f"Error: {str(e)}." # Get just the error message part of the exception
        if processed_messages: # Append any partial messages if they exist
            detailed_error_message += " Partial processing messages: " + " | ".join(processed_messages)
        return False, detailed_error_message

def mark_indent_completed(_engine, indent_id: int, user_id: str, indent_mrn: str) -> Tuple[bool, str]:
    if _engine is None: return False, "Database engine not available."
    if not all([indent_id, user_id, indent_mrn]): return False, "Missing indent_id, user_id, or indent_mrn."
    
    try:
        with _engine.connect() as connection:
            with connection.begin():
                # Mark any remaining 'Pending Issue' or 'Partially Issued' items as 'Item Cancelled'
                # This signifies they won't be issued further under this completion action.
                update_pending_items_sql = text("""
                    UPDATE indent_items 
                    SET item_status = :new_status 
                    WHERE indent_id = :indent_id AND item_status IN (:pending_status, :partial_status);
                """)
                connection.execute(update_pending_items_sql, {
                    "new_status": ITEM_STATUS_CANCELLED_ITEM, 
                    "indent_id": indent_id,
                    "pending_status": ITEM_STATUS_PENDING_ISSUE,
                    "partial_status": ITEM_STATUS_PARTIALLY_ISSUED
                })
                _update_indent_overall_status(connection, indent_id, STATUS_COMPLETED, user_id)
        
        get_indents.clear()
        get_indents_for_processing.clear()
        return True, f"Indent MRN {indent_mrn} successfully marked as {STATUS_COMPLETED}. Any remaining pending/partially issued items were marked as cancelled."
    except Exception as e:
        print(f"ERROR (indent_service): Marking indent {indent_mrn} completed: {e}\n{traceback.format_exc()}")
        return False, f"Error marking indent {indent_mrn} as completed: {e}"

def cancel_entire_indent(_engine, indent_id: int, user_id: str, indent_mrn: str) -> Tuple[bool, str]:
    if _engine is None: return False, "Database engine not available."
    if not all([indent_id, user_id, indent_mrn]): return False, "Missing indent_id, user_id, or indent_mrn."

    try:
        with _engine.connect() as connection:
            with connection.begin():
                # Update items that are not yet fully issued to 'Item Cancelled' status
                update_items_sql = text("""
                    UPDATE indent_items 
                    SET item_status = :cancelled_item_status 
                    WHERE indent_id = :indent_id AND item_status != :fully_issued_status; 
                """)
                connection.execute(update_items_sql, {
                    "cancelled_item_status": ITEM_STATUS_CANCELLED_ITEM, # Use corrected constant
                    "indent_id": indent_id,
                    "fully_issued_status": ITEM_STATUS_FULLY_ISSUED 
                })
                
                _update_indent_overall_status(connection, indent_id, STATUS_CANCELLED, user_id) # Overall indent status
        
        get_indents.clear()
        get_indents_for_processing.clear()
        return True, f"Indent MRN {indent_mrn} and its pending/partially issued items successfully cancelled."
    except Exception as e:
        print(f"ERROR (indent_service): Cancelling indent {indent_mrn}: {e}\n{traceback.format_exc()}")
        return False, f"Error cancelling indent {indent_mrn}: {e}"