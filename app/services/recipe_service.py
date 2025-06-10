"""Service layer for recipe management."""
from typing import Dict, List, Tuple, Any, Optional
import traceback
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.engine import Engine, Connection

from app.core.logging import get_logger
from app.db.database_utils import fetch_data
from app.core.constants import TX_SALE
from . import stock_service

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────
# RECIPE CRUD FUNCTIONS
# ─────────────────────────────────────────────────────────

def list_recipes(
    engine: Engine,
    search_text: Optional[str] = None,
    include_inactive: bool = False,
) -> pd.DataFrame:
    """Return recipes filtered by search text and active status."""
    if engine is None:
        logger.error(
            "ERROR [recipe_service.list_recipes]: Database engine not available."
        )
        return pd.DataFrame()

    ilike_keyword = "ILIKE" if engine.dialect.name == "postgresql" else "LIKE"

    query = "SELECT recipe_id, name, description, is_active FROM recipes WHERE 1=1"
    params: Dict[str, Any] = {}
    if not include_inactive:
        query += " AND is_active = TRUE"
    if search_text and search_text.strip():
        query += f" AND (name {ilike_keyword} :search OR description {ilike_keyword} :search)"
        params["search"] = f"%{search_text.strip()}%"
    query += " ORDER BY name;"
    return fetch_data(engine, query, params)


def get_recipe_items(engine: Engine, recipe_id: int) -> pd.DataFrame:
    """Return ingredient breakdown for a recipe."""
    if engine is None:
        logger.error(
            "ERROR [recipe_service.get_recipe_items]: Database engine not available."
        )
        return pd.DataFrame()
    query = text(
        """
        SELECT ri.recipe_item_id, ri.recipe_id, ri.item_id, i.name AS item_name, ri.quantity
        FROM recipe_items ri
        JOIN items i ON ri.item_id = i.item_id
        WHERE ri.recipe_id = :rid
        ORDER BY i.name;
        """
    )
    return fetch_data(engine, query.text, {"rid": recipe_id})


def create_recipe(
    engine: Engine,
    recipe_data: Dict[str, Any],
    ingredients: List[Dict[str, Any]],
) -> Tuple[bool, str, Optional[int]]:
    """Create a recipe and its ingredient rows."""
    if engine is None:
        return False, "Database engine not available.", None
    if not recipe_data.get("name") or not str(recipe_data.get("name")).strip():
        return False, "Recipe name is required.", None
    if not ingredients:
        return False, "At least one ingredient is required.", None
    clean_name = recipe_data["name"].strip()
    desc = recipe_data.get("description")
    desc_clean = desc.strip() if isinstance(desc, str) and desc.strip() else None
    is_active = bool(recipe_data.get("is_active", True))
    insert_recipe_q = text(
        """INSERT INTO recipes (name, description, is_active) VALUES (:n, :d, :a) RETURNING recipe_id;"""
    )
    insert_item_q = text(
        "INSERT INTO recipe_items (recipe_id, item_id, quantity) VALUES (:r, :i, :q);"
    )
    try:
        with engine.connect() as conn:
            with conn.begin():
                rid = conn.execute(insert_recipe_q, {"n": clean_name, "d": desc_clean, "a": is_active}).scalar_one_or_none()
                if not rid:
                    raise Exception("Failed to insert recipe header.")
                for ing in ingredients:
                    iid = ing.get("item_id")
                    qty = ing.get("quantity", 0)
                    if not iid or qty is None or qty <= 0:
                        raise ValueError("Invalid ingredient data")
                    conn.execute(insert_item_q, {"r": rid, "i": iid, "q": float(qty)})
        return True, f"Recipe '{clean_name}' added.", rid
    except IntegrityError as ie:
        logger.error(
            "ERROR [recipe_service.create_recipe]: Integrity error: %s\n%s",
            ie,
            traceback.format_exc(),
        )
        msg = "Recipe with this name already exists." if "unique" in str(ie).lower() else "Integrity error."
        return False, msg, None
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [recipe_service.create_recipe]: DB error: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred.", None


def update_recipe(
    engine: Engine,
    recipe_id: int,
    recipe_data: Dict[str, Any],
    ingredients: List[Dict[str, Any]],
) -> Tuple[bool, str]:
    """Update recipe details and ingredients."""
    if engine is None:
        return False, "Database engine not available."
    if not recipe_id:
        return False, "Recipe ID required."
    if not recipe_data.get("name") or not str(recipe_data.get("name")).strip():
        return False, "Recipe name is required."
    if not ingredients:
        return False, "At least one ingredient is required."
    clean_name = recipe_data["name"].strip()
    desc = recipe_data.get("description")
    desc_clean = desc.strip() if isinstance(desc, str) and desc.strip() else None
    is_active = bool(recipe_data.get("is_active", True))
    upd_q = text(
        "UPDATE recipes SET name=:n, description=:d, is_active=:a, updated_at=NOW() WHERE recipe_id=:rid;"
    )
    del_items_q = text("DELETE FROM recipe_items WHERE recipe_id=:rid;")
    ins_item_q = text(
        "INSERT INTO recipe_items (recipe_id, item_id, quantity) VALUES (:r, :i, :q);"
    )
    try:
        with engine.connect() as conn:
            with conn.begin():
                res = conn.execute(upd_q, {"n": clean_name, "d": desc_clean, "a": is_active, "rid": recipe_id})
                if res.rowcount == 0:
                    return False, "Recipe not found."
                conn.execute(del_items_q, {"rid": recipe_id})
                for ing in ingredients:
                    iid = ing.get("item_id")
                    qty = ing.get("quantity", 0)
                    if not iid or qty is None or qty <= 0:
                        raise ValueError("Invalid ingredient data")
                    conn.execute(ins_item_q, {"r": recipe_id, "i": iid, "q": float(qty)})
        return True, f"Recipe '{clean_name}' updated."
    except IntegrityError as ie:
        logger.error(
            "ERROR [recipe_service.update_recipe]: Integrity error: %s\n%s",
            ie,
            traceback.format_exc(),
        )
        msg = "Duplicate recipe name." if "unique" in str(ie).lower() else "Integrity error."
        return False, msg
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [recipe_service.update_recipe]: DB error: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred."


def archive_recipe(engine: Engine, recipe_id: int) -> Tuple[bool, str]:
    """Set a recipe's ``is_active`` flag to ``FALSE``."""
    if engine is None:
        return False, "Database engine not available."
    if not recipe_id:
        return False, "Recipe ID required."
    query = text("UPDATE recipes SET is_active = FALSE WHERE recipe_id = :rid;")
    try:
        with engine.connect() as conn:
            with conn.begin():
                result = conn.execute(query, {"rid": recipe_id})
        if result.rowcount > 0:
            return True, "Recipe archived successfully."
        return False, "Recipe not found or already archived."
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [recipe_service.archive_recipe]: DB error: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred."


def reactivate_recipe(engine: Engine, recipe_id: int) -> Tuple[bool, str]:
    """Set a recipe's ``is_active`` flag to ``TRUE``."""
    if engine is None:
        return False, "Database engine not available."
    if not recipe_id:
        return False, "Recipe ID required."
    query = text("UPDATE recipes SET is_active = TRUE WHERE recipe_id = :rid;")
    try:
        with engine.connect() as conn:
            with conn.begin():
                result = conn.execute(query, {"rid": recipe_id})
        if result.rowcount > 0:
            return True, "Recipe reactivated successfully."
        return False, "Recipe not found or already active."
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [recipe_service.reactivate_recipe]: DB error: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred."


def delete_recipe(engine: Engine, recipe_id: int) -> Tuple[bool, str]:
    """Delete a recipe."""
    if engine is None:
        return False, "Database engine not available."
    if not recipe_id:
        return False, "Recipe ID required."
    del_q = text("DELETE FROM recipes WHERE recipe_id=:rid;")
    try:
        success, _ = fetch_data(engine, "SELECT 1").empty, None
        with engine.begin() as conn:
            res = conn.execute(del_q, {"rid": recipe_id})
            if res.rowcount == 0:
                return False, "Recipe not found."
        return True, "Recipe deleted."
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [recipe_service.delete_recipe]: DB error: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred."


# ─────────────────────────────────────────────────────────
# SALES RECORDING USING RECIPES
# ─────────────────────────────────────────────────────────

def record_sale(
    engine: Engine,
    recipe_id: int,
    quantity: float,
    user_id: str,
    notes: Optional[str] = None,
) -> Tuple[bool, str]:
    """Record sale of a recipe and reduce ingredient stock."""
    if engine is None:
        return False, "Database engine not available."
    if not recipe_id or quantity <= 0:
        return False, "Invalid recipe or quantity."
    user_id_clean = user_id.strip() if user_id else "System"
    notes_clean = notes.strip() if isinstance(notes, str) and notes.strip() else None
    sale_ins_q = text(
        "INSERT INTO sales_transactions (recipe_id, quantity, user_id, notes) VALUES (:r, :q, :u, :n);"
    )
    items_df = get_recipe_items(engine, recipe_id)
    if items_df.empty:
        return False, "No ingredients defined for recipe."
    try:
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(sale_ins_q, {"r": recipe_id, "q": quantity, "u": user_id_clean, "n": notes_clean})
                for _, row in items_df.iterrows():
                    total_qty = float(row["quantity"]) * quantity
                    ok = stock_service.record_stock_transaction(
                        item_id=int(row["item_id"]),
                        quantity_change=-total_qty,
                        transaction_type=TX_SALE,
                        user_id=user_id_clean,
                        related_mrn=None,
                        related_po_id=None,
                        notes=f"Recipe {recipe_id} sale",  # type: ignore
                        db_engine_param=None,
                        db_connection_param=conn,
                    )
                    if not ok:
                        raise Exception(
                            f"Failed stock tx for item {row['item_id']} during sale.")
        return True, "Sale recorded."
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [recipe_service.record_sale]: Error recording sale: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred during sale recording."
