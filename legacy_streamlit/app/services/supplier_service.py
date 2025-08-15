# app/services/supplier_service.py
import traceback
from typing import Any, Optional, Dict, Tuple

import pandas as pd
from . import cache_data
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.engine import Engine

from app.core.logging import get_logger
from app.db.database_utils import fetch_data

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────
# SUPPLIER MASTER FUNCTIONS
# ─────────────────────────────────────────────────────────
@cache_data(ttl=300, show_spinner="Fetching supplier data...")
def get_all_suppliers(_engine: Engine, include_inactive=False) -> pd.DataFrame:
    """
    Fetches all suppliers, optionally including inactive ones.
    Args:
        _engine: SQLAlchemy database engine instance.
        include_inactive: Flag to include inactive suppliers.
    Returns:
        Pandas DataFrame of suppliers.
    """
    if _engine is None:
        logger.error(
            "ERROR [supplier_service.get_all_suppliers]: Database engine not available."
        )
        return pd.DataFrame()
    query = "SELECT supplier_id, name, contact_person, phone, email, address, notes, is_active FROM suppliers"
    if not include_inactive:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY name;"
    return fetch_data(_engine, query)


def get_supplier_details(engine: Engine, supplier_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetches details for a specific supplier by ID.
    (This function is NOT CACHED, so no .clear() method is available)
    Args:
        engine: SQLAlchemy database engine instance.
        supplier_id: The ID of the supplier.
    Returns:
        Dictionary of supplier details or None if not found.
    """
    if engine is None:
        logger.error(
            "ERROR [supplier_service.get_supplier_details]: Database engine not available."
        )
        return None
    query = "SELECT supplier_id, name, contact_person, phone, email, address, notes, is_active FROM suppliers WHERE supplier_id = :supplier_id;"
    df = fetch_data(engine, query, {"supplier_id": supplier_id})
    if not df.empty:
        return df.iloc[0].to_dict()
    return None


def add_supplier(engine: Engine, details: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Adds a new supplier to the database.
    Args:
        engine: SQLAlchemy database engine instance.
        details: Dictionary containing supplier details.
    Returns:
        Tuple (success_status, message).
    """
    if engine is None:
        return False, "Database engine not available."
    supplier_name = details.get("name", "").strip()
    if not supplier_name:
        return False, "Supplier name is required and cannot be empty."

    query = text(
        """
        INSERT INTO suppliers (name, contact_person, phone, email, address, notes, is_active)
        VALUES (:name, :contact_person, :phone, :email, :address, :notes, :is_active)
        RETURNING supplier_id;
    """
    )
    params = {
        "name": supplier_name,
        "contact_person": (details.get("contact_person", "").strip() or None),
        "phone": (details.get("phone", "").strip() or None),
        "email": (details.get("email", "").strip() or None),
        "address": (details.get("address", "").strip() or None),
        "notes": (details.get("notes", "").strip() or None),
        "is_active": details.get("is_active", True),
    }
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, params)
                new_id = result.scalar_one_or_none()
        if new_id:
            get_all_suppliers.clear()
            return (
                True,
                f"Supplier '{params['name']}' added successfully with ID {new_id}.",
            )
        else:
            return False, "Failed to add supplier (no ID returned)."
    except IntegrityError:
        return (
            False,
            f"Supplier name '{params['name']}' already exists. Please use a unique name.",
        )
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [supplier_service.add_supplier]: Database error adding supplier: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred while adding the supplier."


def update_supplier(
    engine: Engine, supplier_id: int, updates: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Updates details for an existing supplier.
    Args:
        engine: SQLAlchemy database engine instance.
        supplier_id: The ID of the supplier to update.
        updates: Dictionary of fields to update.
    Returns:
        Tuple (success_status, message).
    """
    if engine is None:
        return False, "Database engine not available."
    if not supplier_id or not updates:
        return False, "Invalid supplier ID or no updates provided."

    supplier_name_update = updates.get("name", "").strip()
    if "name" in updates and not supplier_name_update:
        return False, "Supplier name cannot be empty when provided for update."

    set_clauses = []
    params: Dict[str, Any] = {"supplier_id": supplier_id}
    allowed_fields = ["name", "contact_person", "phone", "email", "address", "notes"]

    for key, value in updates.items():
        if key in allowed_fields:
            set_clauses.append(f"{key} = :{key}")
            current_val = value.strip() if isinstance(value, str) else value
            if key != "name" and current_val == "":
                params[key] = None
            else:
                params[key] = current_val

    if not set_clauses:
        return False, "No valid fields provided for update."

    query_str = f"UPDATE suppliers SET {', '.join(set_clauses)}, updated_at = NOW() WHERE supplier_id = :supplier_id;"
    query = text(query_str)

    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, params)
        if result.rowcount > 0:
            get_all_suppliers.clear()
            return True, f"Supplier ID {supplier_id} updated successfully."
        else:
            existing = get_supplier_details(engine, supplier_id)
            if existing is None:
                return False, f"Update failed: Supplier ID {supplier_id} not found."
            return (
                True,
                f"No changes detected for Supplier ID {supplier_id}. Update considered successful.",
            )
    except IntegrityError:
        return (
            False,
            f"Update failed: Potential duplicate name '{updates.get('name')}'.",
        )
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [supplier_service.update_supplier]: Database error updating supplier %s: %s\n%s",
            supplier_id,
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred while updating the supplier."


def deactivate_supplier(engine: Engine, supplier_id: int) -> Tuple[bool, str]:
    """
    Deactivates a supplier.
    Args:
        engine: SQLAlchemy database engine instance.
        supplier_id: The ID of the supplier to deactivate.
    Returns:
        Tuple (success_status, message).
    """
    if engine is None:
        return False, "Database engine not available."
    query = text(
        "UPDATE suppliers SET is_active = FALSE, updated_at = NOW() WHERE supplier_id = :supplier_id;"
    )
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, {"supplier_id": supplier_id})
        if result.rowcount > 0:
            get_all_suppliers.clear()
            return True, "Supplier deactivated successfully."
        return False, "Supplier not found or already inactive."
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [supplier_service.deactivate_supplier]: Error deactivating supplier %s: %s\n%s",
            supplier_id,
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred."


def reactivate_supplier(engine: Engine, supplier_id: int) -> Tuple[bool, str]:
    """
    Reactivates a supplier.
    Args:
        engine: SQLAlchemy database engine instance.
        supplier_id: The ID of the supplier to reactivate.
    Returns:
        Tuple (success_status, message).
    """
    if engine is None:
        return False, "Database engine not available."
    query = text(
        "UPDATE suppliers SET is_active = TRUE, updated_at = NOW() WHERE supplier_id = :supplier_id;"
    )
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, {"supplier_id": supplier_id})
        if result.rowcount > 0:
            get_all_suppliers.clear()
            return True, "Supplier reactivated successfully."
        return False, "Supplier not found or already active."
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [supplier_service.reactivate_supplier]: Error reactivating supplier %s: %s\n%s",
            supplier_id,
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred."
