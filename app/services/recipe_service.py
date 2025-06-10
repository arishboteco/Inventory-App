from typing import Any, Dict, List, Optional, Tuple
import traceback

import pandas as pd
import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.engine import Engine

from app.core.logging import get_logger
from app.db.database_utils import fetch_data

logger = get_logger(__name__)


@st.cache_data(ttl=300, show_spinner="Fetching recipes...")
def get_all_recipes(engine: Engine, include_inactive: bool = False) -> pd.DataFrame:
    """Return all recipes."""
    if engine is None:
        logger.error("ERROR [recipe_service.get_all_recipes]: engine is None")
        return pd.DataFrame()
    query = "SELECT recipe_id, name, description, is_active FROM recipes"
    if not include_inactive:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY name"
    return fetch_data(engine, query)


def get_recipe_details(engine: Engine, recipe_id: int) -> Optional[Dict[str, Any]]:
    """Return header and ingredient lines for a recipe."""
    if engine is None:
        logger.error("ERROR [recipe_service.get_recipe_details]: engine is None")
        return None
    header_q = "SELECT recipe_id, name, description, is_active FROM recipes WHERE recipe_id = :rid"
    header_df = fetch_data(engine, header_q, {"rid": recipe_id})
    if header_df.empty:
        return None
    items_q = (
        "SELECT ri.recipe_item_id, ri.item_id, i.name AS item_name, ri.quantity "
        "FROM recipe_items ri JOIN items i ON ri.item_id = i.item_id "
        "WHERE ri.recipe_id = :rid ORDER BY item_name"
    )
    items_df = fetch_data(engine, items_q, {"rid": recipe_id})
    return {"header": header_df.iloc[0].to_dict(), "items": items_df.to_dict("records")}


def create_recipe(
    engine: Engine,
    recipe_data: Dict[str, Any],
    items: List[Dict[str, Any]],
) -> Tuple[bool, str]:
    """Insert a new recipe and its ingredient lines."""
    if engine is None:
        return False, "Database engine not available"
    if not recipe_data.get("name"):
        return False, "Recipe name required"
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    "INSERT INTO recipes (name, description, is_active) "
                    "VALUES (:name, :description, :is_active) RETURNING recipe_id"
                ),
                {
                    "name": recipe_data["name"].strip(),
                    "description": recipe_data.get("description"),
                    "is_active": recipe_data.get("is_active", True),
                },
            )
            new_id = result.scalar_one()
            for line in items:
                if not line.get("item_id"):
                    continue
                conn.execute(
                    text(
                        "INSERT INTO recipe_items (recipe_id, item_id, quantity) "
                        "VALUES (:rid, :iid, :qty)"
                    ),
                    {"rid": new_id, "iid": line["item_id"], "qty": line.get("quantity", 0)},
                )
        get_all_recipes.clear()
        return True, f"Recipe added with ID {new_id}"
    except IntegrityError:
        return False, "Recipe with this name already exists"
    except SQLAlchemyError as e:
        logger.error("ERROR [recipe_service.create_recipe]: %s\n%s", e, traceback.format_exc())
        return False, "Database error while creating recipe"


def update_recipe(
    engine: Engine,
    recipe_id: int,
    recipe_data: Dict[str, Any],
    items: List[Dict[str, Any]],
) -> Tuple[bool, str]:
    """Update a recipe header and its ingredient lines."""
    if engine is None:
        return False, "Database engine not available"
    if not recipe_id:
        return False, "Recipe ID required"
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE recipes SET name=:name, description=:description, "
                    "is_active=:is_active, updated_at=NOW() WHERE recipe_id=:rid"
                ),
                {
                    "name": recipe_data.get("name"),
                    "description": recipe_data.get("description"),
                    "is_active": recipe_data.get("is_active", True),
                    "rid": recipe_id,
                },
            )
            conn.execute(text("DELETE FROM recipe_items WHERE recipe_id=:rid"), {"rid": recipe_id})
            for line in items:
                if not line.get("item_id"):
                    continue
                conn.execute(
                    text(
                        "INSERT INTO recipe_items (recipe_id, item_id, quantity) "
                        "VALUES (:rid, :iid, :qty)"
                    ),
                    {"rid": recipe_id, "iid": line["item_id"], "qty": line.get("quantity", 0)},
                )
        get_all_recipes.clear()
        return True, "Recipe updated"
    except IntegrityError:
        return False, "Duplicate recipe name"
    except SQLAlchemyError as e:
        logger.error("ERROR [recipe_service.update_recipe]: %s\n%s", e, traceback.format_exc())
        return False, "Database error while updating recipe"


def deactivate_recipe(engine: Engine, recipe_id: int) -> Tuple[bool, str]:
    """Mark a recipe as inactive."""
    if engine is None:
        return False, "Database engine not available"
    try:
        with engine.begin() as conn:
            res = conn.execute(
                text("UPDATE recipes SET is_active=FALSE, updated_at=NOW() WHERE recipe_id=:rid"),
                {"rid": recipe_id},
            )
        get_all_recipes.clear()
        if res.rowcount:
            return True, "Recipe deactivated"
        return False, "Recipe not found"
    except SQLAlchemyError as e:
        logger.error("ERROR [recipe_service.deactivate_recipe]: %s\n%s", e, traceback.format_exc())
        return False, "Database error while deactivating recipe"
