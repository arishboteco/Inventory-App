# app/services/supplier_service.py
import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, Tuple

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.database_utils import fetch_data

# ─────────────────────────────────────────────────────────
# SUPPLIER MASTER FUNCTIONS
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Fetching supplier data...")
def get_all_suppliers(_engine, include_inactive=False) -> pd.DataFrame:
    if _engine is None: return pd.DataFrame()
    query = "SELECT supplier_id, name, contact_person, phone, email, address, notes, is_active FROM suppliers"
    if not include_inactive:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY name;"
    return fetch_data(_engine, query)

def get_supplier_details(engine, supplier_id: int) -> Optional[Dict[str, Any]]:
    if engine is None: return None
    query = "SELECT supplier_id, name, contact_person, phone, email, address, notes, is_active FROM suppliers WHERE supplier_id = :supplier_id;"
    df = fetch_data(engine, query, {"supplier_id": supplier_id})
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def add_supplier(engine, details: Dict[str, Any]) -> Tuple[bool, str]:
    if engine is None: return False, "Database engine not available."
    if not details.get("name"): return False, "Supplier name is required."
    query = text("""
        INSERT INTO suppliers (name, contact_person, phone, email, address, notes, is_active)
        VALUES (:name, :contact_person, :phone, :email, :address, :notes, :is_active)
        RETURNING supplier_id;
    """)
    params = {
        "name": details.get("name", "").strip(),
        "contact_person": (details.get("contact_person") or "").strip() or None,
        "phone": (details.get("phone") or "").strip() or None,
        "email": (details.get("email") or "").strip() or None,
        "address": (details.get("address") or "").strip() or None,
        "notes": (details.get("notes") or "").strip() or None,
        "is_active": details.get("is_active", True)
    }
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, params)
                new_id = result.scalar_one_or_none()
        if new_id:
            get_all_suppliers.clear() # Clear this service's cache
            return True, f"Supplier '{params['name']}' added with ID {new_id}."
        else:
            return False, "Failed to add supplier."
    except IntegrityError:
        return False, f"Supplier name '{params['name']}' already exists."
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error adding supplier: {e}")
        return False, "Database error adding supplier."

def update_supplier(engine, supplier_id: int, updates: Dict[str, Any]) -> Tuple[bool, str]:
    if engine is None: return False, "Database engine not available."
    if not supplier_id or not updates: return False, "Invalid supplier ID or no updates."
    set_clauses = []
    params = {"supplier_id": supplier_id}
    allowed = ["name", "contact_person", "phone", "email", "address", "notes"]
    for key, value in updates.items():
        if key in allowed:
            set_clauses.append(f"{key} = :{key}")
            params[key] = value.strip() if isinstance(value, str) else value
            if key != "name" and params[key] == "": # Allow setting optional fields to NULL
                 params[key] = None
    if not set_clauses: return False, "No valid fields to update."
    query = text(f"UPDATE suppliers SET {', '.join(set_clauses)} WHERE supplier_id = :supplier_id;")
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, params)
        if result.rowcount > 0:
            get_all_suppliers.clear() # Clear this service's cache
            # If get_supplier_details were cached, clear it too
            return True, f"Supplier ID {supplier_id} updated."
        else:
            existing = get_supplier_details(engine, supplier_id) # Call within service
            if existing is None: return False, f"Update failed: Supplier ID {supplier_id} not found."
            else: return False, f"Supplier ID {supplier_id} found, but no changes were made."
    except IntegrityError:
        return False, f"Update failed: Potential duplicate name '{updates.get('name')}'."
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error updating supplier {supplier_id}: {e}")
        return False, "Database error updating supplier."

def deactivate_supplier(engine, supplier_id: int) -> bool:
    if engine is None: return False
    query = text("UPDATE suppliers SET is_active = FALSE WHERE supplier_id = :supplier_id;")
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, {"supplier_id": supplier_id})
        if result.rowcount > 0:
            get_all_suppliers.clear() # Clear this service's cache
            return True
        return False
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Error deactivating supplier {supplier_id}: {e}")
        return False

def reactivate_supplier(engine, supplier_id: int) -> bool:
    if engine is None: return False
    query = text("UPDATE suppliers SET is_active = TRUE WHERE supplier_id = :supplier_id;")
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, {"supplier_id": supplier_id})
        if result.rowcount > 0:
            get_all_suppliers.clear() # Clear this service's cache
            return True
        return False
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Error reactivating supplier {supplier_id}: {e}")
        return False