"""Service layer for recipe management.

This module provides a light-weight port of the legacy Streamlit
``recipe_service``.  It operates directly on the ``recipes`` and
``recipe_components`` tables using SQLAlchemy connections so it can be used
from the Django app and in tests without depending on the legacy codebase.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger(__name__)

TX_SALE = "SALE"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _strip_or_none(val: Any) -> Optional[str]:
    """Return a stripped string or ``None``."""
    if isinstance(val, str):
        val = val.strip()
        return val or None
    return None


from inventory.models import Item, Recipe

def _component_unit(kind: str, cid: int, unit: Optional[str]) -> Optional[str]:
    """Validate and resolve a component's unit."""
    if kind == "ITEM":
        try:
            item = Item.objects.get(pk=cid)
            if unit is None:
                return item.base_unit
            if unit not in [item.base_unit, item.purchase_unit]:
                raise ValueError("Unit mismatch for item component")
            return unit
        except Item.DoesNotExist:
            raise ValueError(f"Item {cid} not found")
    if kind == "RECIPE":
        try:
            recipe = Recipe.objects.get(pk=cid)
            db_unit = recipe.default_yield_unit
            if unit is not None and db_unit and unit != db_unit:
                raise ValueError("Unit mismatch for recipe component")
            return unit if unit is not None else db_unit
        except Recipe.DoesNotExist:
            raise ValueError(f"Recipe {cid} not found")
    raise ValueError("Invalid component_kind")


from inventory.models import RecipeComponent

def _has_path(start_id: int, target_id: int, visited: Optional[Set[int]] = None) -> bool:
    """Return True if ``start_id`` recipe references ``target_id`` recursively."""
    if visited is None:
        visited = set()
    if start_id in visited:
        return False  # Already checked this path
    visited.add(start_id)

    if start_id == target_id:
        return True

    components = RecipeComponent.objects.filter(parent_recipe_id=start_id, component_kind='RECIPE')
    for component in components:
        if _has_path(component.component_id, target_id, visited):
            return True
    return False


def _creates_cycle(parent_id: int, child_id: int) -> bool:
    """Check whether linking ``parent_id`` -> ``child_id`` creates a cycle."""
    if parent_id == child_id:
        return True
    return _has_path(child_id, parent_id)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def build_components_from_editor(
    df, choice_map: Dict[str, Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Convert a data-editor DataFrame into component payload.

    ``choice_map`` is expected to map the label from the UI to metadata about
    the component (kind, id, unit information etc.).
    """

    from inventory.constants import PLACEHOLDER_SELECT_COMPONENT

    components: List[Dict[str, Any]] = []
    errors: List[str] = []
    for idx, row in df.iterrows():
        label = row.get("component")
        if not label or label == PLACEHOLDER_SELECT_COMPONENT:
            continue
        meta = choice_map.get(label)
        if not meta:
            continue
        qty = row.get("quantity")
        if qty is None or float(qty) <= 0:
            errors.append(f"Quantity must be greater than 0 for {label}.")
            continue
        unit = row.get("unit") or meta.get("base_unit") or meta.get("unit")
        if meta["kind"] == "ITEM":
            base_unit = meta.get("base_unit")
            purchase_unit = meta.get("purchase_unit")
            allowed = {u for u in [base_unit, purchase_unit] if u}
            if unit not in allowed:
                if purchase_unit:
                    errors.append(
                        f"Unit mismatch for {meta.get('name')}. Use {base_unit} or {purchase_unit}."
                    )
                else:
                    errors.append(
                        f"Unit mismatch for {meta.get('name')}. Use {base_unit}."
                    )
                continue
        components.append(
            {
                "component_kind": meta["kind"],
                "component_id": meta["id"],
                "quantity": float(qty),
                "unit": unit,
                "loss_pct": float(row.get("loss_pct") or 0),
                "sort_order": int(row.get("sort_order") or idx + 1),
                "notes": row.get("notes") or None,
            }
        )
    return components, errors


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


from django.db import transaction

@transaction.atomic
def create_recipe(
    data: Dict[str, Any], components: List[Dict[str, Any]]
) -> Tuple[bool, str, Optional[int]]:
    """Create a recipe and associated components."""
    try:
        recipe = Recipe.objects.create(**data)

        for comp_data in components:
            unit = _component_unit(
                comp_data["component_kind"],
                comp_data["component_id"],
                comp_data.get("unit"),
            )
            if comp_data["component_kind"] == "RECIPE" and _creates_cycle(
                recipe.pk, comp_data["component_id"]
            ):
                raise ValueError("Adding this component creates a cycle")

            RecipeComponent.objects.create(
                parent_recipe=recipe,
                component_kind=comp_data["component_kind"],
                component_id=comp_data["component_id"],
                quantity=comp_data["quantity"],
                unit=unit,
                loss_pct=comp_data.get("loss_pct", 0),
                sort_order=comp_data.get("sort_order", 0),
                notes=_strip_or_none(comp_data.get("notes")),
            )

        return True, "Recipe created.", recipe.pk
    except (IntegrityError, ValueError) as exc:
        logger.error("Error creating recipe: %s", exc)
        return False, str(exc), None
    except Exception as exc:
        logger.error("DB error creating recipe: %s", exc)
        return False, "A database error occurred.", None


@transaction.atomic
def update_recipe(
    recipe_id: int,
    data: Dict[str, Any],
    components: List[Dict[str, Any]],
) -> Tuple[bool, str]:
    """Update a recipe and replace its components."""
    try:
        if data:
            Recipe.objects.filter(pk=recipe_id).update(**data)

        RecipeComponent.objects.filter(parent_recipe_id=recipe_id).delete()

        recipe = Recipe.objects.get(pk=recipe_id)
        for comp_data in components:
            unit = _component_unit(
                comp_data["component_kind"],
                comp_data["component_id"],
                comp_data.get("unit"),
            )
            if comp_data["component_kind"] == "RECIPE" and _creates_cycle(
                recipe_id, comp_data["component_id"]
            ):
                raise ValueError("Adding this component creates a cycle")

            RecipeComponent.objects.create(
                parent_recipe=recipe,
                component_kind=comp_data["component_kind"],
                component_id=comp_data["component_id"],
                quantity=comp_data["quantity"],
                unit=unit,
                loss_pct=comp_data.get("loss_pct", 0),
                sort_order=comp_data.get("sort_order", 0),
                notes=_strip_or_none(comp_data.get("notes")),
            )

        return True, "Recipe updated."
    except (IntegrityError, ValueError) as exc:
        logger.error("Error updating recipe: %s", exc)
        return False, str(exc)
    except Exception as exc:
        logger.error("DB error updating recipe: %s", exc)
        return False, "A database error occurred."


# ---------------------------------------------------------------------------
# Sale handling
# ---------------------------------------------------------------------------


def _expand_requirements(
    recipe_id: int,
    multiplier: float,
    totals: Dict[int, float],
    visited: Set[int],
) -> None:
    if recipe_id in visited:
        raise ValueError("Circular reference detected during expansion")
    visited.add(recipe_id)

    components = RecipeComponent.objects.filter(parent_recipe_id=recipe_id)
    for component in components:
        qty = multiplier * float(component.quantity) / (1 - float(component.loss_pct or 0) / 100.0)
        if component.component_kind == "ITEM":
            item = Item.objects.get(pk=component.component_id)
            if not item.is_active:
                raise ValueError("Inactive item component encountered")
            if item.base_unit != component.unit:
                raise ValueError("Unit mismatch for item component")
            totals[component.component_id] = totals.get(component.component_id, 0) + qty
        elif component.component_kind == "RECIPE":
            sub_recipe = Recipe.objects.get(pk=component.component_id)
            if not sub_recipe.is_active:
                raise ValueError("Inactive sub-recipe encountered")
            if not sub_recipe.default_yield_unit:
                raise ValueError("Missing unit for recipe component")
            if sub_recipe.default_yield_unit != component.unit:
                raise ValueError("Unit mismatch for recipe component")
            _expand_requirements(component.component_id, qty, totals, visited)

    visited.remove(recipe_id)


def _resolve_item_requirements(recipe_id: int, quantity: float) -> Dict[int, float]:
    totals: Dict[int, float] = {}
    _expand_requirements(recipe_id, quantity, totals, set())
    return totals


from inventory.models import StockTransaction

@transaction.atomic
def record_sale(
    recipe_id: int,
    quantity: float,
    user_id: str,
    notes: Optional[str] = None,
) -> Tuple[bool, str]:
    """Record sale of a recipe and reduce ingredient stock."""
    if not recipe_id or quantity <= 0:
        return False, "Invalid recipe or quantity."

    try:
        recipe = Recipe.objects.get(pk=recipe_id)
        if not recipe.is_active:
            return False, "Recipe is inactive."

        totals = _resolve_item_requirements(recipe_id, quantity)

        # TODO: Create a SalesTransaction model and uncomment the following lines.
        # SalesTransaction.objects.create(
        #     recipe=recipe,
        #     quantity=quantity,
        #     user_id=user_id,
        #     notes=notes,
        # )

        for item_id, qty in totals.items():
            item = Item.objects.select_for_update().get(pk=item_id)
            item.current_stock -= qty
            item.save()
            StockTransaction.objects.create(
                item=item,
                quantity_change=-qty,
                transaction_type=TX_SALE,
                user_id=user_id,
                notes=f"Recipe {recipe_id} sale",
            )

        return True, "Sale recorded."
    except Recipe.DoesNotExist:
        return False, "Recipe not found."
    except Item.DoesNotExist as e:
        return False, str(e)
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        logger.error("Error recording sale: %s", e)
        return False, "A database error occurred."
