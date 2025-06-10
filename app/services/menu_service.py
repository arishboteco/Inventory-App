"""Service layer for menu items management."""
from typing import Any, Dict, Optional, Tuple
import pandas as pd
import streamlit as st  # For caching hints
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.engine import Engine

from app.core.logging import get_logger
from app.db.database_utils import fetch_data

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────
# MENU ITEM FUNCTIONS
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Fetching menu items...")
def get_all_menu_items(engine: Engine, include_inactive: bool = False) -> pd.DataFrame:
    """Return all menu items joined with item details."""
    if engine is None:
        logger.error(
            "ERROR [menu_service.get_all_menu_items]: Database engine not available."
        )
        return pd.DataFrame()
    query = (
        "SELECT mi.menu_item_id, mi.item_id, i.name, i.unit, mi.is_active "
        "FROM menu_items mi JOIN items i ON mi.item_id = i.item_id"
    )
    if not include_inactive:
        query += " WHERE mi.is_active = TRUE"
    query += " ORDER BY i.name;"
    return fetch_data(engine, query)


def add_menu_item(engine: Engine, item_id: int, is_active: bool = True) -> Tuple[bool, str, Optional[int]]:
    """Add a new menu item referencing an inventory item."""
    if engine is None:
        return False, "Database engine not available.", None
    if not item_id:
        return False, "Item ID required.", None
    query = text(
        "INSERT INTO menu_items (item_id, is_active) VALUES (:i, :a) RETURNING menu_item_id;"
    )
    try:
        with engine.begin() as conn:
            new_id = conn.execute(query, {"i": item_id, "a": is_active}).scalar_one_or_none()
        if new_id:
            get_all_menu_items.clear()
            return True, "Menu item added.", new_id
        return False, "Insert failed.", None
    except IntegrityError:
        return False, "Menu item already exists for this item.", None
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [menu_service.add_menu_item]: DB error: %s", e
        )
        return False, "A database error occurred.", None


def deactivate_menu_item(engine: Engine, menu_item_id: int) -> Tuple[bool, str]:
    """Deactivate a menu item."""
    if engine is None:
        return False, "Database engine not available."
    query = text("UPDATE menu_items SET is_active=FALSE WHERE menu_item_id=:m;")
    try:
        with engine.begin() as conn:
            res = conn.execute(query, {"m": menu_item_id})
        if res.rowcount:
            get_all_menu_items.clear()
            return True, "Menu item deactivated."
        return False, "Menu item not found."
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [menu_service.deactivate_menu_item]: DB error: %s", e
        )
        return False, "A database error occurred."


def reactivate_menu_item(engine: Engine, menu_item_id: int) -> Tuple[bool, str]:
    """Reactivate a menu item."""
    if engine is None:
        return False, "Database engine not available."
    query = text("UPDATE menu_items SET is_active=TRUE WHERE menu_item_id=:m;")
    try:
        with engine.begin() as conn:
            res = conn.execute(query, {"m": menu_item_id})
        if res.rowcount:
            get_all_menu_items.clear()
            return True, "Menu item reactivated."
        return False, "Menu item not found."
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [menu_service.reactivate_menu_item]: DB error: %s", e
        )
        return False, "A database error occurred."
