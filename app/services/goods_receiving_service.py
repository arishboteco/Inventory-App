# app/services/goods_receiving_service.py
import streamlit as st
import pandas as pd
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime
import traceback 

from sqlalchemy import text 
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.database_utils import fetch_data
from app.services import stock_service
from app.services import purchase_order_service 
from app.core.constants import (
    TX_RECEIVING, 
    PO_STATUS_PARTIALLY_RECEIVED, PO_STATUS_FULLY_RECEIVED,
    PO_STATUS_ORDERED, PO_STATUS_CANCELLED
)

def generate_grn_number(engine) -> Optional[str]:
    if engine is None: print("ERROR (GRN Service): Database engine not available for GRN Number generation."); return None
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT nextval('grn_sequence');")) 
            seq_num = result.scalar_one()
            return f"GRN-{datetime.now().strftime('%Y%m')}-{seq_num:04d}"
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR (GRN Service): Error generating GRN Number: {e}"); return None

def create_grn(engine, grn_data: Dict[str, Any], items_received_data: List[Dict[str, Any]]) -> Tuple[bool, str, Optional[int]]:
    if engine is None: return False, "Database engine not available.", None
    required_header = ["supplier_id", "received_date", "received_by_user_id"]
    if not all(grn_data.get(f) for f in required_header):
        return False, f"Missing GRN header fields: {', '.join(f for f in required_header if not grn_data.get(f))}", None
    if not items_received_data: return False, "GRN must contain at least one item.", None

    for i, item in enumerate(items_received_data):
        try:
            qty = float(item.get('quantity_received', 0)); price = float(item.get('unit_price_at_receipt', 0))
            if not item.get('item_id') or qty <= 0 or price < 0:
                return False, f"Invalid data in received item line {i+1}: Check Item, Quantity (>0), or Price (>=0).", None
        except (ValueError, TypeError): return False, f"Invalid numeric data for qty/price in item line {i+1}.", None
            
    new_grn_number = generate_grn_number(engine)
    if not new_grn_number: return False, "Failed to generate GRN Number.", None

    header_q_obj = text("""INSERT INTO goods_received_notes (grn_number, po_id, supplier_id, received_date, notes, received_by_user_id, created_at)
                       VALUES (:grn_number, :po_id, :supplier_id, :received_date, :notes, :received_by_user_id, NOW()) RETURNING grn_id;""")
    item_q_obj = text("""INSERT INTO grn_items (grn_id, item_id, po_item_id, quantity_ordered_on_po, quantity_received, unit_price_at_receipt, notes)
                    VALUES (:grn_id, :item_id, :po_item_id, :quantity_ordered_on_po, :quantity_received, :unit_price_at_receipt, :item_notes);""")
    
    header_p = {"grn_number": new_grn_number, "po_id": grn_data.get('po_id'), "supplier_id": grn_data['supplier_id'],
                  "received_date": grn_data['received_date'], "notes": (grn_data.get('notes', '').strip() or None),
                  "received_by_user_id": grn_data['received_by_user_id']}
    new_grn_id: Optional[int] = None
    try:
        with engine.connect() as conn: 
            with conn.begin():
                print(f"DEBUG (GRN Service): Attempting to insert GRN header for GRN: {new_grn_number}")
                res = conn.execute(header_q_obj, header_p); new_grn_id = res.scalar_one_or_none()
                if not new_grn_id: raise Exception("Failed to retrieve grn_id after GRN header insertion.")
                print(f"DEBUG (GRN Service): GRN header inserted. new_grn_id: {new_grn_id}")

                item_p_list = []
                for item_d in items_received_data:
                    qty_rcv = float(item_d['quantity_received']); price_rcv = float(item_d['unit_price_at_receipt'])
                    
                    # ** CORRECTED ITEM NOTES HANDLING **
                    item_notes_val = item_d.get('item_notes') # Get raw value
                    cleaned_item_notes = None
                    if isinstance(item_notes_val, str):
                        cleaned_item_notes = item_notes_val.strip()
                        if not cleaned_item_notes: # If stripping results in an empty string
                            cleaned_item_notes = None
                    # If item_notes_val was None initially, cleaned_item_notes remains None

                    item_p_list.append({"grn_id": new_grn_id, "item_id": item_d['item_id'], "po_item_id": item_d.get('po_item_id'),
                                          "quantity_ordered_on_po": item_d.get('quantity_ordered_on_po'), "quantity_received": qty_rcv,
                                          "unit_price_at_receipt": price_rcv, "item_notes": cleaned_item_notes }) # Use cleaned_item_notes
                    
                    print(f"DEBUG (GRN Service): Calling stock_service for item_id {item_d['item_id']}, qty_change {qty_rcv}")
                    stock_ok = stock_service.record_stock_transaction(
                        item_id=item_d['item_id'], quantity_change=qty_rcv, transaction_type=TX_RECEIVING,
                        user_id=grn_data['received_by_user_id'], related_po_id=grn_data.get('po_id'),
                        notes=f"GRN: {new_grn_number}", db_engine_param=None, db_connection_param=conn 
                    )
                    if not stock_ok: 
                        raise Exception(f"Failed to record stock transaction for item_id {item_d['item_id']} on GRN {new_grn_number}.")
                
                if item_p_list: 
                    print(f"DEBUG (GRN Service): Attempting to insert {len(item_p_list)} GRN items.")
                    conn.execute(item_q_obj, item_p_list) 
                    print(f"DEBUG (GRN Service): GRN items inserted.")

                po_id_to_update = grn_data.get('po_id')
                if po_id_to_update:
                    print(f"DEBUG (GRN Service): Updating PO status for po_id: {po_id_to_update}")
                    po_items_query_str = "SELECT po_item_id, item_id, quantity_ordered FROM purchase_order_items WHERE po_id = :po_id"
                    po_items_df = fetch_data(conn, po_items_query_str, {"po_id": po_id_to_update})
                    print(f"DEBUG (GRN Service): PO Items for po_id {po_id_to_update}: \n{po_items_df.to_string()}")
                    
                    grn_items_sum_query_str = """SELECT po_item_id, SUM(quantity_received) as total_received 
                                               FROM grn_items gi
                                               JOIN goods_received_notes g ON gi.grn_id = g.grn_id 
                                               WHERE g.po_id = :po_id AND gi.po_item_id IS NOT NULL
                                               GROUP BY gi.po_item_id"""
                    grn_items_sum_df = fetch_data(conn, grn_items_sum_query_str, {"po_id": po_id_to_update})
                    print(f"DEBUG (GRN Service): Sum of GRN Items for po_id {po_id_to_update} (after current GRN insertion): \n{grn_items_sum_df.to_string()}")

                    new_po_stat = PO_STATUS_PARTIALLY_RECEIVED 
                    if not po_items_df.empty:
                        all_fulfilled = True
                        for _, po_row in po_items_df.iterrows():
                            po_item_id, item_id_on_po, ordered = po_row['po_item_id'], po_row['item_id'], float(po_row['quantity_ordered'])
                            received_rows = grn_items_sum_df[grn_items_sum_df['po_item_id'] == po_item_id]
                            total_rcv = float(received_rows.iloc[0]['total_received']) if not received_rows.empty else 0.0
                            print(f"DEBUG (GRN Service): PO Item ID {po_item_id} (Item ID {item_id_on_po}): Ordered: {ordered}, Total Rcvd: {total_rcv}")
                            if total_rcv < ordered: all_fulfilled = False; print(f"DEBUG (GRN Service): Item ID {item_id_on_po} NOT fully received."); break 
                        if all_fulfilled: new_po_stat = PO_STATUS_FULLY_RECEIVED; print(f"DEBUG (GRN Service): All items on PO {po_id_to_update} fully received.")
                    else: new_po_stat = PO_STATUS_FULLY_RECEIVED; print(f"DEBUG (GRN Service): PO {po_id_to_update} has no items; marking fully received.")
                    
                    print(f"DEBUG (GRN Service): Determined new PO status for {po_id_to_update}: {new_po_stat}")
                    update_po_q_obj = text("UPDATE purchase_orders SET status = :status, updated_at = NOW() WHERE po_id = :po_id AND status NOT IN (:fully_received, :cancelled);")
                    update_res = conn.execute(update_po_q_obj, {"status": new_po_stat, "po_id": po_id_to_update, "fully_received": PO_STATUS_FULLY_RECEIVED, "cancelled": PO_STATUS_CANCELLED})
                    print(f"DEBUG (GRN Service): PO status update rowcount for po_id {po_id_to_update}: {update_res.rowcount}")
                    
                    purchase_order_service.list_pos.clear()
                    purchase_order_service.get_po_by_id.clear() 
        
        return True, f"GRN {new_grn_number} created. Stock updated. PO status updated.", new_grn_id
    except IntegrityError as e:
        msg = "DB integrity error creating GRN."
        if "goods_received_notes_grn_number_key" in str(e).lower(): msg = f"GRN Number '{new_grn_number}' conflict."
        print(f"ERROR (GRN Service): {msg} Details: {e}\n{traceback.format_exc()}"); return False, msg, None
    except Exception as e: 
        print(f"ERROR (GRN Service): Error during GRN creation for {new_grn_number}: {e}\n{traceback.format_exc()}"); 
        return False, f"A database error occurred: {e}", None

def get_received_quantities_for_po(_engine, po_id: int) -> pd.DataFrame:
    if _engine is None or not po_id:
        return pd.DataFrame(columns=['po_item_id', 'total_previously_received'])
    query_string = """
        SELECT gi.po_item_id, SUM(gi.quantity_received) as total_previously_received
        FROM grn_items gi
        JOIN goods_received_notes g ON gi.grn_id = g.grn_id
        WHERE g.po_id = :po_id AND gi.po_item_id IS NOT NULL
        GROUP BY gi.po_item_id;
    """
    df = fetch_data(_engine, query_string, {"po_id": po_id}) 
    if 'total_previously_received' not in df.columns:
        df['total_previously_received'] = 0.0 
    else:
        df['total_previously_received'] = pd.to_numeric(df['total_previously_received'], errors='coerce').fillna(0)
    if 'po_item_id' not in df.columns:
         df['po_item_id'] = pd.Series(dtype='Int64') 
    return df

@st.cache_data(ttl=120, show_spinner="Fetching GRN list...")
def list_grns(_engine, filters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    if _engine is None: return pd.DataFrame()
    query_list_grn_str = """SELECT g.grn_id, g.grn_number, g.po_id, po.po_number, g.supplier_id, s.name AS supplier_name,
                               g.received_date, g.notes, g.received_by_user_id, g.created_at
                           FROM goods_received_notes g JOIN suppliers s ON g.supplier_id = s.supplier_id
                           LEFT JOIN purchase_orders po ON g.po_id = po.po_id WHERE 1=1"""
    params_list_grn = {}
    if filters:
        if filters.get("grn_number_ilike"): query_list_grn_str += " AND g.grn_number ILIKE :grn_number"; params_list_grn["grn_number"] = f"%{filters['grn_number_ilike']}%"
        if filters.get("supplier_id"): query_list_grn_str += " AND g.supplier_id = :supplier_id"; params_list_grn["supplier_id"] = filters["supplier_id"]
        if filters.get("po_number_ilike"): query_list_grn_str += " AND po.po_number ILIKE :po_number"; params_list_grn["po_number"] = f"%{filters['po_number_ilike']}%"
    query_list_grn_str += " ORDER BY g.received_date DESC, g.created_at DESC;"
    return fetch_data(_engine, query_list_grn_str, params_list_grn)

@st.cache_data(ttl=60, show_spinner="Fetching GRN details...")
def get_grn_details(_engine, grn_id: int) -> Optional[Dict[str, Any]]:
    if _engine is None or not grn_id: return None
    grn_header_query_str = """SELECT g.grn_id, g.grn_number, g.po_id, po.po_number, g.supplier_id, s.name as supplier_name,
                                   g.received_date, g.notes, g.received_by_user_id, g.created_at
                               FROM goods_received_notes g JOIN suppliers s ON g.supplier_id = s.supplier_id
                               LEFT JOIN purchase_orders po ON g.po_id = po.po_id WHERE g.grn_id = :grn_id;"""
    grn_items_query_str = """SELECT gi.grn_item_id, gi.item_id, i.name as item_name, i.unit as item_unit,
                                   gi.po_item_id, gi.quantity_ordered_on_po, gi.quantity_received,
                                   gi.unit_price_at_receipt, gi.notes as item_notes
                               FROM grn_items gi JOIN items i ON gi.item_id = i.item_id
                               WHERE gi.grn_id = :grn_id ORDER BY i.name;"""
    try:
        grn_header_df = fetch_data(_engine, grn_header_query_str, {"grn_id": grn_id})
        if grn_header_df.empty: return None
        
        grn_header = grn_header_df.iloc[0].to_dict()
        grn_items_df = fetch_data(_engine, grn_items_query_str, {"grn_id": grn_id})
        grn_header["items"] = grn_items_df.to_dict(orient='records')
        return grn_header
    except (SQLAlchemyError, Exception) as e:
        print(f"ERROR (GRN Service): DB error fetching GRN details for grn_id {grn_id}: {e}"); return None