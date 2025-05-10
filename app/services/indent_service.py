# app/services/indent_service.py
import streamlit as st
import pandas as pd
from typing import Optional, Dict, List, Tuple, Any # Ensure all needed types are here
from datetime import datetime, timedelta, date # Ensure all needed datetime parts

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.database_utils import fetch_data
from app.core.constants import STATUS_SUBMITTED # create_indent uses this default

# Note: No direct dependency on item_service or other services from here,
# unless, for example, create_indent needed to directly check item existence
# or update something in another service (which it currently doesn't).

# ─────────────────────────────────────────────────────────
# INDENT FUNCTIONS
# ─────────────────────────────────────────────────────────
def generate_mrn(engine) -> Optional[str]:
    if engine is None: return None
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT nextval('mrn_seq');"))
            seq_num = result.scalar_one()
            return f"MRN-{datetime.now().strftime('%Y%m')}-{seq_num:05d}"
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Error generating MRN: Sequence 'mrn_seq' might not exist or other DB error. {e}")
        return None

def create_indent(engine, indent_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Tuple[bool, str]:
    if engine is None: return False, "Database engine not available."
    required_header = ["mrn", "requested_by", "department", "date_required"]
    missing_or_empty = [k for k in required_header if not indent_data.get(k) or (isinstance(indent_data.get(k), str) and not indent_data.get(k).strip())]
    if missing_or_empty: return False, f"Missing or empty required indent header fields: {', '.join(missing_or_empty)}"
    if not items_data: return False, "Indent must contain at least one item."

    for i, item in enumerate(items_data):
        if not item.get('item_id') or not item.get('requested_qty') or item['requested_qty'] <= 0:
            return False, f"Invalid data in item row {i+1}: {item}. Ensure item ID and positive quantity are present."

    indent_query = text("""
        INSERT INTO indents (mrn, requested_by, department, date_required, notes, status, date_submitted)
        VALUES (:mrn, :requested_by, :department, :date_required, :notes, :status, NOW())
        RETURNING indent_id;
    """)
    item_query = text("""
        INSERT INTO indent_items (indent_id, item_id, requested_qty, notes)
        VALUES (:indent_id, :item_id, :requested_qty, :notes);
    """)
    notes_value = indent_data.get("notes")
    cleaned_notes = notes_value.strip() if isinstance(notes_value, str) else None
    indent_params = {
        "mrn": indent_data["mrn"].strip(),
        "requested_by": indent_data["requested_by"].strip(),
        "department": indent_data["department"],
        "date_required": indent_data["date_required"],
        "notes": cleaned_notes,
        "status": indent_data.get("status", STATUS_SUBMITTED) # Uses imported constant
    }
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(indent_query, indent_params)
                new_indent_id = result.scalar_one_or_none()
                if not new_indent_id: raise Exception("Failed to retrieve indent_id after insertion.")
                item_params_list = [{"indent_id": new_indent_id, "item_id": item['item_id'],
                                     "requested_qty": float(item['requested_qty']),
                                     "notes": (item.get('notes') or "").strip() or None} for item in items_data]
                connection.execute(item_query, item_params_list)
        get_indents.clear() # Clear this service's cache for indent list
        return True, f"Indent {indent_data['mrn']} created successfully."
    except IntegrityError as e:
        error_msg = f"Database integrity error creating indent. Check MRN uniqueness and Item IDs."
        if "indents_mrn_key" in str(e): error_msg = f"Failed to create indent: MRN '{indent_params['mrn']}' already exists."
        elif "indent_items_item_id_fkey" in str(e): error_msg = "Failed to create indent: One or more selected Item IDs are invalid."
        st.error(error_msg + f" Details: {e}")
        return False, error_msg.split('.')[0] # Return simpler part of the message
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error creating indent: {e}")
        return False, "Database error creating indent."

@st.cache_data(ttl=120, show_spinner="Fetching indent list...")
def get_indents(
    _engine, mrn_filter: Optional[str] = None, dept_filter: Optional[str] = None,
    status_filter: Optional[str] = None, date_start_str: Optional[str] = None,
    date_end_str: Optional[str] = None
) -> pd.DataFrame:
    if _engine is None: return pd.DataFrame()
    date_start_filter, date_end_filter = None, None
    if date_start_str:
        try: date_start_filter = datetime.strptime(date_start_str, '%Y-%m-%d').date()
        except ValueError: st.warning(f"Invalid start date format: {date_start_str}. Ignoring.")
    if date_end_str:
        try: date_end_filter = datetime.strptime(date_end_str, '%Y-%m-%d').date()
        except ValueError: st.warning(f"Invalid end date format: {date_end_str}. Ignoring.")

    query = """
        SELECT i.indent_id, i.mrn, i.requested_by, i.department, i.date_required,
               i.date_submitted, i.status, i.notes AS indent_notes, COUNT(ii.indent_item_id) AS item_count
        FROM indents i LEFT JOIN indent_items ii ON i.indent_id = ii.indent_id WHERE 1=1
    """
    params = {}
    if mrn_filter: query += " AND i.mrn ILIKE :mrn"; params['mrn'] = f"%{mrn_filter}%"
    if dept_filter: query += " AND i.department = :department"; params['department'] = dept_filter
    if status_filter: query += " AND i.status = :status"; params['status'] = status_filter
    if date_start_filter: query += " AND i.date_submitted >= :date_from"; params['date_from'] = date_start_filter
    if date_end_filter:
        effective_date_to = date_end_filter + timedelta(days=1)
        query += " AND i.date_submitted < :date_to"; params['date_to'] = effective_date_to
    query += """
        GROUP BY i.indent_id, i.mrn, i.requested_by, i.department, i.date_required,
                 i.date_submitted, i.status, i.notes
        ORDER BY i.date_submitted DESC, i.indent_id DESC
    """
    df = fetch_data(_engine, query, params)
    if not df.empty:
        for col in ['date_required', 'date_submitted']:
             if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce')
        if 'item_count' in df.columns:
             df['item_count'] = pd.to_numeric(df['item_count'], errors='coerce').fillna(0).astype(int)
    return df

def get_indent_details_for_pdf(engine, mrn: str) -> Tuple[Optional[Dict], Optional[List[Dict]]]:
    if engine is None or not mrn: return None, None
    header_data, items_data = None, None
    try:
        with engine.connect() as connection:
            header_query = text("""
                SELECT ind.indent_id, ind.mrn, ind.department, ind.requested_by,
                       ind.date_submitted, ind.date_required, ind.status, ind.notes
                FROM indents ind WHERE ind.mrn = :mrn;
            """)
            header_result = connection.execute(header_query, {"mrn": mrn}).mappings().first()
            if not header_result:
                st.error(f"Indent with MRN '{mrn}' not found.")
                return None, None
            header_data = dict(header_result)
            if header_data.get('date_submitted'):
                header_data['date_submitted'] = pd.to_datetime(header_data['date_submitted']).strftime('%Y-%m-%d %H:%M')
            if header_data.get('date_required'):
                 header_data['date_required'] = pd.to_datetime(header_data['date_required']).strftime('%Y-%m-%d')

            items_query = text("""
                SELECT ii.item_id, i.name AS item_name, i.unit AS item_unit,
                       ii.requested_qty, ii.notes AS item_notes
                FROM indent_items ii
                JOIN items i ON ii.item_id = i.item_id
                JOIN indents ind ON ii.indent_id = ind.indent_id
                WHERE ind.mrn = :mrn ORDER BY i.name;
            """)
            items_result = connection.execute(items_query, {"mrn": mrn}).mappings().all()
            items_data = [dict(row) for row in items_result]
        return header_data, items_data
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error fetching details for indent {mrn}: {e}")
        return None, None