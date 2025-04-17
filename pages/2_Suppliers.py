# item_manager_app.py  – FULL VERSION (incl. get_supplier_details)
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError
import pandas as pd
from typing import Any, Optional, Dict, List
from datetime import datetime, date, timedelta

# ─────────────────────────────────────────────────────────
# CONSTANTS
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
# DB CONNECTION
# ─────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Connecting to database…")
def connect_db():
    try:
        if "database" not in st.secrets:
            st.error("Database configuration missing.")
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
# ITEM FUNCTIONS
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner="Fetching items…")
def get_all_items_with_stock(_engine,
                             include_inactive: bool = False,
                             department: Optional[str] = None) -> pd.DataFrame:
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
    df = df.loc[:, ~df.columns.duplicated()]
    return df

# (Item CRUD functions omitted for brevity …)

# ─────────────────────────────────────────────────────────
# SUPPLIER FUNCTIONS
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_all_suppliers(engine, include_inactive=False):
    sql = "SELECT * FROM suppliers"
    if not include_inactive:
        sql += " WHERE is_active=TRUE"
    return fetch_data(engine, sql + " ORDER BY name")

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# NEW: single‑supplier look‑up  (needed by Suppliers page)
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
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
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

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
# (Stock transactions, indents, dashboard code continues…)
# ─────────────────────────────────────────────────────────
# -- the remainder of the file is unchanged from the previous version --
# -- keep your stock transaction functions, MRN / indent functions,  --
# -- and the dashboard UI section here.                               --
