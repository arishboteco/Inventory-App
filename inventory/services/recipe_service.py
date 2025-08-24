from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from django.db import IntegrityError, transaction

from ..models import Item, Recipe, RecipeComponent, SaleTransaction, StockTransaction

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


def _component_unit(kind: str, cid: int, unit: Optional[str]) -> Optional[str]:
    """Validate and resolve a component's unit.

    For ``ITEM`` components the unit must match the item's ``base_unit``.
    For ``RECIPE`` components the unit must match the child recipe's
    ``default_yield_unit``.
    """

    if kind == "ITEM":
        item = Item.objects.filter(pk=cid).values("base_unit").first()
        if not item:
            raise ValueError(f"Item {cid} not found")
        base = item["base_unit"]
        if unit is None:
            return base
        if unit != base:
            raise ValueError("Unit mismatch for item component")
        return unit
    if kind == "RECIPE":
        rec = Recipe.objects.filter(pk=cid).values("default_yield_unit").first()
        db_unit = rec["default_yield_unit"] if rec else None
        if unit is not None and db_unit and unit != db_unit:
            raise ValueError("Unit mismatch for recipe component")
        return unit if unit is not None else db_unit
    raise ValueError("Invalid component_kind")


def _has_path(start: int, target: int) -> bool:
    """Return True if ``start`` recipe references ``target`` recursively."""
    if start == target:
        return True
    children = RecipeComponent.objects.filter(
        parent_recipe_id=start, component_kind="RECIPE"
    ).values_list("component_id", flat=True)
    for cid in children:
        if _has_path(cid, target):
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


def _row_to_dict(obj: Any) -> Dict[str, Any]:
    """Return a dict for ``obj`` supporting pydantic models."""

    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()  # type: ignore[no-any-return]
    if hasattr(obj, "dict"):
        return obj.dict()  # type: ignore[no-any-return]
    return {k: getattr(obj, k) for k in dir(obj) if not k.startswith("_")}


def build_components_from_editor(
    rows: Iterable[Any],
    choice_map: Dict[str, Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Convert an iterable of editor rows into component payload.

    ``choice_map`` is expected to map the label from the UI to metadata about
    the component (kind, id, unit information etc.). ``rows`` may contain
    dictionaries, Pydantic models or similar objects.
    """

    from inventory.constants import PLACEHOLDER_SELECT_COMPONENT

    components: List[Dict[str, Any]] = []
    errors: List[str] = []
    for idx, row in enumerate(rows):
        row = _row_to_dict(row)
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


def get_recipe_components(recipe_id: int):
    """Return queryset of components for a recipe ordered by sort order."""
    return RecipeComponent.objects.filter(parent_recipe_id=recipe_id).order_by(
        "sort_order", "id"
    )


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


def create_recipe(
    data: Dict[str, Any], components: List[Dict[str, Any]]
) -> Tuple[bool, str, Optional[int]]:
    """Create a recipe and associated components."""
    try:
        with transaction.atomic():
            fields = {
                "name": data.get("name"),
                "description": data.get("description"),
                "is_active": data.get("is_active"),
                "type": data.get("type"),
                "default_yield_qty": data.get("default_yield_qty"),
                "default_yield_unit": data.get("default_yield_unit"),
                "plating_notes": data.get("plating_notes"),
                "tags": data.get("tags"),
            }
            recipe = Recipe.objects.create(**fields)
            for comp in components:
                unit = _component_unit(
                    comp["component_kind"],
                    comp["component_id"],
                    comp.get("unit"),
                )
                if comp["component_kind"] == "RECIPE" and _creates_cycle(
                    recipe.recipe_id, comp["component_id"]
                ):
                    raise ValueError("Adding this component creates a cycle")
                RecipeComponent.objects.create(
                    parent_recipe=recipe,
                    component_kind=comp["component_kind"],
                    component_id=comp["component_id"],
                    quantity=comp["quantity"],
                    unit=unit,
                    loss_pct=comp.get("loss_pct") or 0,
                    sort_order=comp.get("sort_order") or 0,
                    notes=_strip_or_none(comp.get("notes")),
                )
        return True, "Recipe created.", recipe.recipe_id
    except (IntegrityError, ValueError) as exc:
        logger.error("Error creating recipe: %s", exc)
        return False, str(exc), None


def update_recipe(
    recipe_id: int, data: Dict[str, Any], components: List[Dict[str, Any]]
) -> Tuple[bool, str]:
    """Update a recipe and replace its components."""
    try:
        with transaction.atomic():
            recipe = Recipe.objects.get(pk=recipe_id)
            for k, v in data.items():
                setattr(recipe, k, v)
            recipe.save()
            RecipeComponent.objects.filter(parent_recipe=recipe).delete()
            for comp in components:
                unit = _component_unit(
                    comp["component_kind"],
                    comp["component_id"],
                    comp.get("unit"),
                )
                if comp["component_kind"] == "RECIPE" and _creates_cycle(
                    recipe_id, comp["component_id"]
                ):
                    raise ValueError("Adding this component creates a cycle")
                RecipeComponent.objects.create(
                    parent_recipe=recipe,
                    component_kind=comp["component_kind"],
                    component_id=comp["component_id"],
                    quantity=comp["quantity"],
                    unit=unit,
                    loss_pct=comp.get("loss_pct") or 0,
                    sort_order=comp.get("sort_order") or 0,
                    notes=_strip_or_none(comp.get("notes")),
                )
        return True, "Recipe updated."
    except Recipe.DoesNotExist:
        return False, "Recipe not found."
    except (IntegrityError, ValueError) as exc:
        logger.error("Error updating recipe: %s", exc)
        return False, str(exc)


def delete_recipe(recipe_id: int) -> Tuple[bool, str]:
    """Delete a recipe and its components."""
    try:
        with transaction.atomic():
            try:
                recipe = Recipe.objects.get(pk=recipe_id)
            except Recipe.DoesNotExist:
                return False, "Recipe not found."
            RecipeComponent.objects.filter(parent_recipe=recipe).delete()
            recipe.delete()
        return True, "Recipe deleted."
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("DB error deleting recipe: %s", exc)
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
    rows = RecipeComponent.objects.filter(parent_recipe_id=recipe_id).values(
        "component_kind", "component_id", "quantity", "unit", "loss_pct"
    )
    for row in rows:
        qty = (
            multiplier
            * float(row["quantity"])
            / (1 - float(row.get("loss_pct") or 0) / 100.0)
        )
        if row["component_kind"] == "ITEM":
            item = (
                Item.objects.filter(pk=row["component_id"])
                .values("base_unit", "is_active")
                .first()
            )
            if not item:
                raise ValueError(f"Item {row['component_id']} not found")
            if not item["is_active"]:
                raise ValueError("Inactive item component encountered")
            if item["base_unit"] != row["unit"]:
                raise ValueError("Unit mismatch for item component")
            totals[row["component_id"]] = totals.get(row["component_id"], 0) + qty
        elif row["component_kind"] == "RECIPE":
            sub = (
                Recipe.objects.filter(pk=row["component_id"])
                .values("default_yield_unit", "is_active")
                .first()
            )
            if not sub:
                raise ValueError(f"Recipe {row['component_id']} not found")
            if not sub["is_active"]:
                raise ValueError("Inactive sub-recipe encountered")
            if not sub["default_yield_unit"]:
                raise ValueError("Missing unit for recipe component")
            if sub["default_yield_unit"] != row["unit"]:
                raise ValueError("Unit mismatch for recipe component")
            _expand_requirements(row["component_id"], qty, totals, visited)
        else:
            raise ValueError("Invalid component_kind")
    visited.remove(recipe_id)


def _resolve_item_requirements(recipe_id: int, quantity: float) -> Dict[int, float]:
    totals: Dict[int, float] = {}
    _expand_requirements(recipe_id, quantity, totals, set())
    return totals


def record_sale(
    recipe_id: int,
    quantity: Decimal,
    user_id: str,
    notes: Optional[str] = None,
) -> Tuple[bool, str]:
    """Record sale of a recipe and reduce ingredient stock."""
    quantity = Decimal(str(quantity))
    if not recipe_id or quantity <= 0:
        return False, "Invalid recipe or quantity."
    user_id_clean = user_id.strip() if user_id else "System"
    notes_clean = _strip_or_none(notes)
    try:
        with transaction.atomic():
            recipe = Recipe.objects.get(pk=recipe_id)
            if not recipe.is_active:
                return False, "Recipe is inactive."
            totals = _resolve_item_requirements(recipe_id, float(quantity))
            SaleTransaction.objects.create(
                recipe=recipe,
                quantity=quantity,
                user_id=user_id_clean,
                notes=notes_clean,
            )
            for iid, qty in totals.items():
                qty_dec = Decimal(str(qty))
                item = Item.objects.get(pk=iid)
                item.current_stock = (item.current_stock or Decimal("0")) - qty_dec
                item.save(update_fields=["current_stock"])
                StockTransaction.objects.create(
                    item=item,
                    quantity_change=Decimal("-1") * qty_dec,
                    transaction_type=TX_SALE,
                    user_id=user_id_clean,
                    notes=f"Recipe {recipe_id} sale",
                )
        return True, "Sale recorded."
    except Recipe.DoesNotExist:
        return False, "Recipe not found."
    except (Item.DoesNotExist, ValueError) as ve:
        logger.error("Error recording sale: %s", ve)
        return False, str(ve)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("DB error recording sale: %s", exc)
        return False, "A database error occurred during sale recording."
