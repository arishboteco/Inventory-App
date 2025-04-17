# item_manager_app.py  – FULL VERSION (19 Apr 2025)

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError
import pandas as pd
from typing import Any, Optional, Dict, List
from datetime import datetime, date, timedelta

# ─────────────────────────────────────────────────────────
# 1. CONSTANTS
# ─────────────────────────────────────────────────────────
TX_RECEIVING       = "RECEIVING"
TX_ADJUSTMENT      = "ADJUSTMENT"
TX_WASTAGE         = "WASTAGE"
TX_INDENT_FULFILL  = "INDENT_FULFILL"
TX_SALE            = "SALE"

STATUS_SUBMITTED   = "Submitted"
STATUS_PROCESSING  = "Processing"
STATUS_COMPLETED   = "Completed"
STATUS_CANCELLED   = "Cancelled"
ALL_INDENT_STATUSES = [
    STATUS_SUBMITTED, STATUS_PROCESSING, STATUS_COMPLETED, STATUS_CANCELLED
]

# ─────────────────────────────────────────────────────────
# 2. DB CONNECTION
# ─────────────────────────────────────────────────────────
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
        eng = create_engine(url, pool_pre_ping=True)
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        return eng
    except Exception as e:
        st.error(f"DB connection error: {e}")
        return None


def fetch_data(engine, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(query), parameters=params or {})
            return pd.DataFrame(rows.fetchall(), columns=rows.keys())
    except Exception as e:
        st.error(f"Fetch error: {e}")
        return pd.DataFrame()

# ─────────────────────────────────────────────────────────
# 3. ITEM FUNCTIONS
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner="Fetching items…")
def get_all_items_with_stock(_engine,
                             include_inactive: bool = False,
                             department: Optional[str] = None) -> pd.DataFrame:
    """
    Returns items plus calculated current_stock.
    Leading underscore tells Streamlit not to hash the SQLAlchemy engine.
    """
    where, params = [], {}
    if not include_inactive:
        where.append("i.is_active = TRUE")
    if department:
        where.append("(i.permitted_departments = 'All' "
                     "OR i.permitted_departments ILIKE :dept)")
        params["dept"] = f"%{department}%"
    clause = "WHERE " + " AND ".join(where) if where else ""
    sql = f"""
        SELECT i.*,
               COALESCE(s.calculated_stock,0) AS current_stock
        FROM items i
        LEFT JOIN (
            SELECT item_id, SUM(quantity_change) AS calculated_stock
            FROM stock_transactions GROUP BY item_id
        ) s ON s.item_id = i.item_id
        {clause}
        ORDER BY i.name
    """
    df = fetch_data(_engine, sql, params)
    df = df.loc[:, ~df.columns.duplicated()]  # drop duplicate cols
    return df


def get_item_details(engine, item_id: int):
    df = fetch_data(engine, "SELECT * FROM items WHERE item_id=:id", {"id": item_id})
    return df.iloc[0].to_dict() if not df.empty else None


def add_new_item(engine, name, unit, category, sub_category,
                 permitted_departments, reorder_point, notes) -> bool:
    q = text("""
        INSERT INTO items
        (name, unit, category, sub_category, permitted_departments,
         reorder_point, notes, is_active)
        VALUES (:name,:unit,:category,:sub_category,:permitted_departments,
                :reorder_point,:notes,TRUE)
        ON CONFLICT (name) DO NOTHING
    """)
    try:
        with engine.begin() as conn:
            r = conn.execute(q, locals())
        get_all_items_with_stock.clear()
        return r.rowcount > 0
    except IntegrityError:
        st.error(f"Item “{name}” already exists.")
    except Exception as e:
        st.error(f"Error adding item: {e}")
    return False


def update_item_details(engine, item_id: int, d: Dict[str, Any]) -> bool:
    d["item_id"] = item_id
    q = text("""
        UPDATE items SET
          name=:name, unit=:unit, category=:category, sub_category=:sub_category,
          permitted_departments=:permitted_departments, reorder_point=:reorder_point,
          notes=:notes
        WHERE item_id=:item_id
    """)
    try:
        with engine.begin() as conn:
            r = conn.execute(q, d)
        get_all_items_with_stock.clear()
        return r.rowcount > 0
    except IntegrityError:
        st.error(f"Name “{d['name']}” already exists.")
    except Exception as e:
        st.error(f"Error updating item: {e}")
    return False


def update_item_status(engine, item_id: int, active: bool) -> bool:
    q = text("UPDATE items SET is_active=:active WHERE item_id=:item_id")
    try:
        with engine.begin() as conn:
            r = conn.execute(q, {"active": active, "item_id": item_id})
        get_all_items_with_stock.clear()
        return r.rowcount > 0
    except Exception as e:
        st.error(f"Status update error: {e}")
        return False


deactivate_item  = lambda eng, iid: update_item_status(eng, iid, False)
reactivate_item  = lambda eng, iid: update_item_status(eng, iid, True)

# ─────────────────────────────────────────────────────────
# 4. SUPPLIER FUNCTIONS
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_all_suppliers(engine, include_inactive=False):
    sql = "SELECT * FROM suppliers"
    if not include_inactive:
        sql += " WHERE is_active=TRUE"
    return fetch_data(engine, sql + " ORDER BY name")

# --- Newly re‑added single‑supplier look‑up ---------------
def get_supplier_details(engine, supplier_id: int) -> Optional[Dict[str, Any]]:
    """
    Return a single supplier row as a dict, or None if not found.
    """
    df = fetch_data(
        engine,
        "SELECT * FROM suppliers WHERE supplier_id = :sid",
        {"sid": supplier_id},
    )
    return df.iloc[0].to_dict() if not df.empty else None
# ----------------------------------------------------------

def add_supplier(engine, name, contact, phone, email, address, notes) -> bool:
    q = text("""
        INSERT INTO suppliers
        (name, contact_person, phone, email, address, notes, is_active)
        VALUES (:name,:contact,:phone,:email,:address,:notes,TRUE)
        ON CONFLICT (name) DO NOTHING
    """)
    try:
        with engine.begin() as conn:
            r = conn.execute(q, locals())
        get_all_suppliers.clear()
        return r.rowcount > 0
    except IntegrityError:
        st.error(f"Supplier “{name}” exists.")
    except Exception as e:
        st.error(f"Error adding supplier: {e}")
    return False


def update_supplier(engine, supplier_id: int, d: Dict[str, Any]) -> bool:
    d["supplier_id"] = supplier_id
    q = text("""
        UPDATE suppliers SET
          name=:name, contact_person=:contact_person, phone=:phone,
          email=:email, address=:address, notes=:notes
        WHERE supplier_id=:supplier_id
    """)
    try:
        with engine.begin() as conn:
            r = conn.execute(q, d)
        get_all_suppliers.clear()
        return r.rowcount > 0
    except IntegrityError:
        st.error(f"Name “{d['name']}” exists.")
    except Exception as e:
        st.error(f"Supplier update error: {e}")
    return False


_supplier_status = lambda eng, sid, act: fetch_data(
    eng,
    "UPDATE suppliers SET is_active=:a WHERE supplier_id=:s RETURNING 1",
    {"a": act, "s": sid}
).shape[0] > 0

deactivate_supplier = lambda eng, sid: _supplier_status(eng, sid, False)
reactivate_supplier = lambda eng, sid: _supplier_status(eng, sid, True)

# ─────────────────────────────────────────────────────────
# 5. STOCK TRANSACTIONS
# ─────────────────────────────────────────────────────────
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
                "item_id": item_id, "qty": qty, "tx_type": tx_type,
                "user": user, "related_mrn": related_mrn,
                "related_po_id": related_po_id, "notes": notes
            })
        get_all_items_with_stock.clear()
        return True
    except Exception as e:
        st.error(f"Transaction error: {e}")
        return False


@st.cache_data(ttl=300)
def get_stock_transactions(engine,
                           item_id: Optional[int] = None,
                           start: Optional[date] = None,
                           end: Optional[date] = None,
                           limit: int = 1000) -> pd.DataFrame:
    cond, p = [], {"limit": limit}
    if item_id: cond.append("st.item_id=:item"); p["item"] = item_id
    if start:   cond.append("st.transaction_date>=:s"); p["s"] = start
    if end:     cond.append("st.transaction_date<:e");  p["e"] = end + timedelta(days=1)
    where = "WHERE " + " AND ".join(cond) if cond else ""
    sql = f"""
        SELECT st.transaction_date, st.transaction_type, st.quantity_change,
               i.name AS item_name, st.user_id, st.related_mrn, st.notes
        FROM stock_transactions st
        JOIN items i ON i.item_id = st.item_id
        {where}
        ORDER BY st.transaction_date DESC LIMIT :limit
    """
    return fetch_data(engine, sql, p)

# ─────────────────────────────────────────────────────────
# 6. MRN & INDENTS
# ─────────────────────────────────────────────────────────
def generate_mrn(engine):
    try:
        with engine.connect() as conn:
            seq = conn.execute(text("SELECT nextval('mrn_seq')")).scalar()
        return f"MRN-{seq:04d}" if seq else None
    except Exception as e:
        st.error(f"MRN generation error: {e}")
        return None


def create_indent(engine, hdr: Dict[str, Any], items: List[Dict[str, Any]]) -> bool:
    if not hdr or not items:
        st.error("Empty indent header/items")
        return False
    try:
        with engine.begin() as conn:
            indent_id = conn.execute(
                text("""
                    INSERT INTO indents
                    (mrn, requested_by, department, date_required,
                     status, date_submitted, notes)
                    VALUES (:mrn,:requested_by,:department,:date_required,
                            :status,CURRENT_TIMESTAMP,:notes)
                    RETURNING indent_id
                """), hdr).scalar_one()
            conn.execute(
                text("""INSERT INTO indent_items
                    (indent_id,item_id,requested_qty,notes)
                    VALUES (:indent_id,:item_id,:requested_qty,:notes)"""),
                [
                    {"indent_id": indent_id,
                     "item_id": i["item_id"],
                     "requested_qty": i["requested_qty"],
                     "notes": i.get("notes")}
                    for i in items
                ]
            )
        return True
    except Exception as e:
        st.error(f"Indent creation error: {e}")
        return False


@st.cache_data(ttl=120)
def get_indents(engine,
                mrn_filter: Optional[str] = None,
                dept_filter: Optional[List[str]] = None,
                status_filter: Optional[List[str]] = None,
                start: Optional[date] = None,
                end: Optional[date] = None,
                limit: int = 500) -> pd.DataFrame:
    cond, p = [], {"limit": limit}
    if mrn_filter: cond.append("ind.mrn ILIKE :mrn"); p["mrn"] = f"%{mrn_filter.strip()}%"
    if dept_filter: cond.append("ind.department = ANY(:dept)"); p["dept"] = dept_filter
    if status_filter: cond.append("ind.status = ANY(:status)"); p["status"] = status_filter
    if start: cond.append("ind.date_submitted>=:s"); p["s"] = start
    if end: cond.append("ind.date_submitted<:e"); p["e"] = end + timedelta(days=1)
    where = "WHERE " + " AND ".join(cond) if cond else ""
    sql = f"""
        SELECT indent_id, mrn, requested_by, department,
               date_required, date_submitted, status, notes
        FROM indents ind {where}
        ORDER BY date_submitted DESC LIMIT :limit
    """
    return fetch_data(engine, sql, p)

# ─────────────────────────────────────────────────────────
# 7. DASHBOARD UI
# ─────────────────────────────────────────────────────────
st.set_page_config(page_title="Inv Manager", page_icon="🍲", layout="wide")
st.title("🍲 Restaurant Inventory Dashboard")
st.caption(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

engine = connect_db()
if not engine: st.stop()
st.sidebar.success("DB connected")

items_df = get_all_items_with_stock(engine)
total_active = len(items_df)

# Low stock (rp > 0)
low_df, low_cnt = pd.DataFrame(), 0
if not items_df.empty:
    try:
        cs = pd.to_numeric(items_df["current_stock"], errors="coerce")
        rp = pd.to_numeric(items_df["reorder_point"], errors="coerce")
        mask = (cs <= rp) & (rp > 0) & cs.notna() & rp.notna()
        low_df = items_df[mask]; low_cnt = len(low_df)
    except Exception as e:
        st.error(f"Low‑stock calc error: {e}")

k1, k2 = st.columns(2)
k1.metric("Active Items", total_active)
k2.metric("Low Stock Items", low_cnt)

st.divider()
st.subheader("⚠️ Low Stock Items")
if low_df.empty:
    st.info("No items currently below reorder level.")
else:
    st.dataframe(
        low_df,
        use_container_width=True,
        hide_index=True,
        column_order=[
            "item_id","name","current_stock","reorder_point",
            "unit","category","sub_category"
        ]
    )

st.divider()
st.markdown("*(additional dashboard widgets here)*")
