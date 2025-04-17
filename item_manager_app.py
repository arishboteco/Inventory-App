# item_manager_app.py  – FULL VERSION (UnhashableParamError fixed)
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple
from datetime import datetime, date, timedelta
import math
import time

# ────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ────────────────────────────────────────────────────────────────────────────
TX_RECEIVING = "RECEIVING"
TX_ADJUSTMENT = "ADJUSTMENT"
TX_WASTAGE = "WASTAGE"
TX_INDENT_FULFILL = "INDENT_FULFILL"
TX_SALE = "SALE"

STATUS_SUBMITTED = "Submitted"
STATUS_PROCESSING = "Processing"
STATUS_COMPLETED = "Completed"
STATUS_CANCELLED = "Cancelled"
ALL_INDENT_STATUSES = [
    STATUS_SUBMITTED,
    STATUS_PROCESSING,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
]

# ────────────────────────────────────────────────────────────────────────────
# DB CONNECTION
# ────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Connecting to database…")
def connect_db():
    try:
        if "database" not in st.secrets:
            st.error("Database configuration missing in secrets.toml")
            return None
        db = st.secrets["database"]
        url = (
            f"{db['engine']}://{db['user']}:{db['password']}"
            f"@{db['host']}:{db['port']}/{db['dbname']}"
        )
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"DB connection error: {e}")
        return None


def fetch_data(engine, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), parameters=params or {})
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# ────────────────────────────────────────────────────────────────────────────
# ITEM  FUNCTIONS
# ────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner="Fetching items…")
def get_all_items_with_stock(_engine,
                             include_inactive: bool = False,
                             department: Optional[str] = None) -> pd.DataFrame:
    """ `_engine` is un‑hashable, the leading underscore tells Streamlit not to hash it. """
    conditions, params = [], {}
    if not include_inactive:
        conditions.append("i.is_active = TRUE")
    if department:
        conditions.append("(i.permitted_departments = 'All' OR i.permitted_departments ILIKE :dept)")
        params["dept"] = f"%{department}%"
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"""
        SELECT i.*,
               COALESCE(s.calculated_stock, 0) AS current_stock
        FROM items i
        LEFT JOIN (
            SELECT item_id, SUM(quantity_change) AS calculated_stock
            FROM stock_transactions GROUP BY item_id
        ) s ON i.item_id = s.item_id
        {where_clause}
        ORDER BY i.name
    """
    df = fetch_data(_engine, query, params)
    df = df.loc[:, ~df.columns.duplicated()]  # drop duplicate cols
    return df
def get_item_details(engine, item_id: int) -> Optional[Dict[str, Any]]:
    df = fetch_data(engine, "SELECT * FROM items WHERE item_id = :id", {"id": item_id})
    return df.iloc[0].to_dict() if not df.empty else None


def add_new_item(engine, name, unit, category, sub_category,
                 permitted_departments, reorder_point, notes) -> bool:
    q = text("""
        INSERT INTO items
        (name, unit, category, sub_category, permitted_departments,
         reorder_point, notes, is_active)
        VALUES (:name, :unit, :category, :sub_category,
                :permitted_departments, :reorder_point, :notes, TRUE)
        ON CONFLICT (name) DO NOTHING
    """)
    try:
        with engine.begin() as conn:
            result = conn.execute(q, locals())
        get_all_items_with_stock.clear()
        return result.rowcount > 0
    except IntegrityError:
        st.error(f"Item “{name}” already exists.")
    except Exception as e:
        st.error(f"Error adding item: {e}")
    return False


def update_item_details(engine, item_id: int, details: Dict[str, Any]) -> bool:
    details["item_id"] = item_id
    q = text("""
        UPDATE items SET
          name=:name, unit=:unit, category=:category, sub_category=:sub_category,
          permitted_departments=:permitted_departments, reorder_point=:reorder_point,
          notes=:notes
        WHERE item_id=:item_id
    """)
    try:
        with engine.begin() as conn:
            result = conn.execute(q, details)
        get_all_items_with_stock.clear()
        return result.rowcount > 0
    except IntegrityError:
        st.error(f"Name “{details['name']}” already exists.")
    except Exception as e:
        st.error(f"Error updating item: {e}")
    return False


def update_item_status(engine, item_id: int, active: bool) -> bool:
    q = text("UPDATE items SET is_active=:active WHERE item_id=:item_id")
    try:
        with engine.begin() as conn:
            result = conn.execute(q, {"active": active, "item_id": item_id})
        get_all_items_with_stock.clear()
        return result.rowcount > 0
    except Exception as e:
        st.error(f"Error updating status: {e}")
        return False


def deactivate_item(engine, item_id: int) -> bool:
    return update_item_status(engine, item_id, False)


def reactivate_item(engine, item_id: int) -> bool:
    return update_item_status(engine, item_id, True)

# ────────────────────────────────────────────────────────────────────────────
# SUPPLIER  FUNCTIONS  (unchanged)
# ────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_all_suppliers(engine, include_inactive=False) -> pd.DataFrame:
    qry = "SELECT * FROM suppliers"
    if not include_inactive:
        qry += " WHERE is_active = TRUE"
    return fetch_data(engine, qry + " ORDER BY name")


def add_supplier(engine, name, contact, phone, email, address, notes) -> bool:
    q = text("""
        INSERT INTO suppliers
        (name, contact_person, phone, email, address, notes, is_active)
        VALUES (:name,:contact,:phone,:email,:address,:notes, TRUE)
        ON CONFLICT (name) DO NOTHING
    """)
    try:
        with engine.begin() as conn:
            result = conn.execute(q, locals())
        get_all_suppliers.clear()
        return result.rowcount > 0
    except IntegrityError:
        st.error(f"Supplier “{name}” exists.")
    except Exception as e:
        st.error(f"Error adding supplier: {e}")
    return False


def update_supplier(engine, supplier_id: int, details: Dict[str, Any]) -> bool:
    details["supplier_id"] = supplier_id
    q = text("""
        UPDATE suppliers SET
          name=:name, contact_person=:contact_person, phone=:phone,
          email=:email, address=:address, notes=:notes
        WHERE supplier_id=:supplier_id
    """)
    try:
        with engine.begin() as conn:
            result = conn.execute(q, details)
        get_all_suppliers.clear()
        return result.rowcount > 0
    except IntegrityError:
        st.error(f"Name “{details['name']}” exists.")
    except Exception as e:
        st.error(f"Error updating supplier: {e}")
    return False


def deactivate_supplier(engine, supplier_id: int) -> bool:
    return _supplier_status(engine, supplier_id, False)


def reactivate_supplier(engine, supplier_id: int) -> bool:
    return _supplier_status(engine, supplier_id, True)


def _supplier_status(engine, supplier_id: int, active: bool) -> bool:
    q = text("UPDATE suppliers SET is_active=:active WHERE supplier_id=:supplier_id")
    try:
        with engine.begin() as conn:
            result = conn.execute(q, {"active": active, "supplier_id": supplier_id})
        get_all_suppliers.clear()
        return result.rowcount > 0
    except Exception as e:
        st.error(f"Error updating supplier: {e}")
        return False

# ────────────────────────────────────────────────────────────────────────────
# STOCK  TRANSACTIONS
# ────────────────────────────────────────────────────────────────────────────
def record_stock_transaction(engine, item_id: int, qty: float, tx_type: str,
                             user: Optional[str] = None,
                             related_mrn: Optional[str] = None,
                             related_po_id: Optional[int] = None,
                             notes: Optional[str] = None) -> bool:
    q = text("""
        INSERT INTO stock_transactions
        (item_id, quantity_change, transaction_type, transaction_date,
         user_id, related_mrn, related_po_id, notes)
        VALUES (:item_id,:qty,:tx_type,CURRENT_TIMESTAMP,
                :user,:related_mrn,:related_po_id,:notes)
    """)
    try:
        with engine.begin() as conn:
            conn.execute(q, {
                "item_id": item_id,
                "qty": qty,
                "tx_type": tx_type,
                "user": user,
                "related_mrn": related_mrn,
                "related_po_id": related_po_id,
                "notes": notes,
            })
        get_all_items_with_stock.clear()
        return True
    except Exception as e:
        st.error(f"Error recording transaction: {e}")
        return False


@st.cache_data(ttl=300)
def get_stock_transactions(engine,
                           item_id: Optional[int] = None,
                           start_date: Optional[date] = None,
                           end_date: Optional[date] = None,
                           limit: int = 1000) -> pd.DataFrame:
    conditions, params = [], {"limit": limit}
    if item_id:
        conditions.append("st.item_id=:item")
        params["item"] = item_id
    if start_date:
        conditions.append("st.transaction_date >= :start")
        params["start"] = start_date
    if end_date:
        conditions.append("st.transaction_date < :end")
        params["end"] = end_date + timedelta(days=1)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    qry = f"""
        SELECT st.transaction_date, st.transaction_type, st.quantity_change,
               i.name AS item_name, st.user_id, st.related_mrn, st.notes
        FROM stock_transactions st
        JOIN items i ON i.item_id = st.item_id
        {where} ORDER BY st.transaction_date DESC LIMIT :limit
    """
    return fetch_data(engine, qry, params)

# ────────────────────────────────────────────────────────────────────────────
# MRN GENERATION & INDENT  CREATION
# ────────────────────────────────────────────────────────────────────────────
def generate_mrn(engine) -> Optional[str]:
    try:
        with engine.connect() as conn:
            seq = conn.execute(text("SELECT nextval('mrn_seq')")).scalar()
        return f"MRN-{seq:04d}" if seq else None
    except Exception as e:
        st.error(f"Error generating MRN: {e}")
        return None


def create_indent(engine,
                  indent_hdr: Dict[str, Any],
                  item_list: List[Dict[str, Any]]) -> bool:
    if not indent_hdr or not item_list:
        st.error("Empty indent header or item list.")
        return False
    try:
        with engine.begin() as conn:
            hdr_q = text("""
                INSERT INTO indents
                (mrn, requested_by, department, date_required,
                 status, date_submitted, notes)
                VALUES
                (:mrn,:requested_by,:department,:date_required,
                 :status,CURRENT_TIMESTAMP,:notes)
                RETURNING indent_id
            """)
            indent_id = conn.execute(hdr_q, indent_hdr).scalar_one()
            item_q = text("""
                INSERT INTO indent_items
                (indent_id, item_id, requested_qty, notes)
                VALUES (:indent_id, :item_id, :requested_qty, :notes)
            """)
            conn.execute(item_q, [
                {"indent_id": indent_id,
                 "item_id": itm["item_id"],
                 "requested_qty": itm["requested_qty"],
                 "notes": itm.get("notes")}
                for itm in item_list
            ])
        return True
    except Exception as e:
        st.error(f"Error creating indent: {e}")
        return False


@st.cache_data(ttl=120)
def get_indents(engine,
                mrn_filter: Optional[str] = None,
                dept_filter: Optional[List[str]] = None,
                status_filter: Optional[List[str]] = None,
                start: Optional[date] = None,
                end: Optional[date] = None,
                limit: int = 500) -> pd.DataFrame:
    params, cond = {"limit": limit}, []
    if mrn_filter:
        cond.append("ind.mrn ILIKE :mrn")
        params["mrn"] = f"%{mrn_filter.strip()}%"
    if dept_filter:
        cond.append("ind.department = ANY(:dept)")
        params["dept"] = dept_filter
    if status_filter:
        cond.append("ind.status = ANY(:status)")
        params["status"] = status_filter
    if start:
        cond.append("ind.date_submitted >= :start")
        params["start"] = start
    if end:
        cond.append("ind.date_submitted < :end")
        params["end"] = end + timedelta(days=1)
    where = "WHERE " + " AND ".join(cond) if cond else ""
    qry = f"""
        SELECT indent_id, mrn, requested_by, department,
               date_required, date_submitted, status, notes
        FROM indents ind {where}
        ORDER BY date_submitted DESC LIMIT :limit
    """
    return fetch_data(engine, qry, params)

# ────────────────────────────────────────────────────────────────────────────
# DASHBOARD UI
# ────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Inv. Manager", page_icon="🍲", layout="wide")
st.title("🍲 Restaurant Inventory Dashboard")
st.caption(f"Time {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

engine = connect_db()
if not engine:
    st.stop()

st.sidebar.success("Connected to DB")

# fetch item list once
items_df = get_all_items_with_stock(engine, include_inactive=False)
total_active_items = len(items_df)

# ---- low‑stock calc (safe) ----
low_df = pd.DataFrame()
low_cnt = 0
if not items_df.empty:
    try:
        cs = items_df.get("current_stock")
        rp = items_df.get("reorder_point")
        if isinstance(cs, pd.Series) and isinstance(rp, pd.Series):
            cs_num = pd.to_numeric(cs, errors="coerce")
            rp_num = pd.to_numeric(rp, errors="coerce")
            mask = (
                (cs_num <= rp_num)
                & rp_num.notna()           # allow 0, just exclude NULL
                & cs_num.notna()
            )
            low_df = items_df[mask]
            low_cnt = len(low_df)
    except Exception as e:
        st.error(f"Low‑stock calc error: {e}")

# ---- KPIs ----
k1, k2 = st.columns(2)
k1.metric("Total Active Items", total_active_items)
k2.metric("Items Low on Stock", low_cnt)

# ---- Low stock table ----
st.divider()
st.subheader("⚠️  Low Stock Items")
if low_df.empty:
    st.info("No items currently flagged as low stock.")
else:
    st.warning("The following items need replenishment:")
    st.dataframe(
        low_df,
        use_container_width=True,
        hide_index=True,
        column_order=[
            "item_id", "name", "current_stock", "reorder_point",
            "unit", "category", "sub_category"
        ],
    )

st.divider()
st.markdown("*(Additional dashboard sections go here…)*")
