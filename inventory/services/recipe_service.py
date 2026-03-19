from __future__ import annotations

import json
import logging
from decimal import Decimal
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from django.contrib.staticfiles.storage import staticfiles_storage
from django.db import IntegrityError, transaction
from django.templatetags.static import static

from inventory.constants import PLACEHOLDER_SELECT_COMPONENT

from ..models import Item, Recipe, RecipeItem, SaleTransaction, StockTransaction
from .item_service import get_unit_display_name
from .stock_utils import get_low_stock_items

logger = logging.getLogger(__name__)

TX_SALE = "SALE"

PLATING_IMAGE_BASE_PATH = "img/plating"
PLATING_IMAGE_EXTENSIONS = (".webp", ".jpg", ".jpeg", ".png", ".svg")
PLATING_PLACEHOLDER_PATH = "img/recipe-placeholder.svg"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


@lru_cache(maxsize=256)
def get_plating_image_url(recipe_id: Optional[int]) -> str:
    """Return the best-guess plating image URL for ``recipe_id``.

    The helper attempts to locate a static asset matching the recipe id using a
    handful of common image extensions. When no dedicated thumbnail exists (or
    ``recipe_id`` is ``None``) the shared placeholder thumbnail is returned
    instead so the UI never renders a broken image.
    """

    placeholder_url = get_plating_placeholder_url()
    if not recipe_id:
        return placeholder_url

    base_path = f"{PLATING_IMAGE_BASE_PATH}/{recipe_id}"
    for extension in PLATING_IMAGE_EXTENSIONS:
        candidate = f"{base_path}{extension}"
        try:
            if staticfiles_storage.exists(candidate):
                return static(candidate)
        except Exception:  # pragma: no cover - defensive
            logger.debug("Unable to resolve plating image for %s", candidate)
            continue
    return placeholder_url


@lru_cache(maxsize=1)
def get_plating_placeholder_url() -> str:
    """Return the shared placeholder thumbnail URL."""

    return static(PLATING_PLACEHOLDER_PATH)


def _strip_or_none(val: Any) -> Optional[str]:
    """Return a stripped string or ``None``."""
    if isinstance(val, str):
        val = val.strip()
        return val or None
    return None


def _parse_tags(tags: Any) -> List[str]:
    """Normalize ``tags`` into a list of strings."""
    if not tags:
        return []
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]
    if isinstance(tags, str):
        tags = tags.strip()
        if not tags:
            return []
        try:
            parsed = json.loads(tags)
            if isinstance(parsed, list):
                return [str(t).strip() for t in parsed if str(t).strip()]
            return [str(parsed).strip()]
        except json.JSONDecodeError:
            return [t.strip() for t in tags.split(",") if t.strip()]
    return [str(tags).strip()]


def _has_path(start: int, target: int) -> bool:
    """Return True if ``start`` recipe references ``target`` recursively."""
    if start == target:
        return True
    # For now, simplified model doesn't support sub-recipes
    # This function can be enhanced later if sub-recipe functionality is needed
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


def build_items_from_editor(
    rows: Iterable[Any],
    choice_map: Dict[str, Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Convert an iterable of editor rows into item payload.

    ``choice_map`` is expected to map the label from the UI to metadata about
    the item (id, unit information etc.). ``rows`` may contain
    dictionaries, Pydantic models or similar objects.
    """

    items: List[Dict[str, Any]] = []
    errors: List[str] = []
    for idx, row in enumerate(rows):
        row = _row_to_dict(row)
        label = row.get("item")
        if not label or label == PLACEHOLDER_SELECT_COMPONENT:
            continue
        meta = choice_map.get(label)
        if not meta:
            continue
        qty = row.get("quantity")
        if qty is None or float(qty) <= 0:
            errors.append(f"Quantity must be greater than 0 for {label}.")
            continue
        unit = row.get("unit")
        # For items, use the item's unit
        allowed_unit = get_unit_display_name(meta.get("unit_id"))
        if unit is None:
            unit = allowed_unit  # Autofill
        elif unit != allowed_unit:
            # For now, no sub-recipe support, so just check basic unit matching
            errors.append(f"Unit mismatch for {meta.get('name')}. Use {allowed_unit}.")
            continue
        items.append(
            {
                "item_id": meta["id"],
                "quantity": float(qty),
                "unit": unit,
                "loss_pct": float(row.get("loss_pct") or 0),
                "sort_order": int(row.get("sort_order") or idx + 1),
                "notes": row.get("notes") or None,
            }
        )
    return items, errors


def get_recipe_items(recipe_id: int):
    """Return queryset of items for a recipe ordered by sort order."""
    return RecipeItem.objects.filter(recipe_id=recipe_id).order_by("sort_order", "id")


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


def create_recipe(
    data: Dict[str, Any], items: List[Dict[str, Any]]
) -> Tuple[bool, str, Optional[int]]:
    """Create a recipe and associated items."""
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
                "tags": _parse_tags(data.get("tags")),
            }
            recipe = Recipe.objects.create(**fields)
            for item_data in items:
                # For now, just create the item without cycle checking
                # Cycle checking would be complex with the item-based approach
                RecipeItem.objects.create(
                    recipe=recipe,
                    item_id=item_data["item_id"],
                    quantity=item_data["quantity"],
                    unit=item_data["unit"],
                    loss_pct=item_data.get("loss_pct") or 0,
                    sort_order=item_data.get("sort_order") or 0,
                    notes=_strip_or_none(item_data.get("notes")),
                )
        return True, "Recipe created.", recipe.recipe_id
    except (IntegrityError, ValueError) as exc:
        logger.error("Error creating recipe: %s", exc)
        return False, str(exc), None


def update_recipe(
    recipe_id: int, data: Dict[str, Any], items: List[Dict[str, Any]]
) -> Tuple[bool, str]:
    """Update a recipe and replace its items."""
    try:
        with transaction.atomic():
            recipe = Recipe.objects.get(pk=recipe_id)
            for k, v in data.items():
                if k == "tags":
                    setattr(recipe, k, _parse_tags(v))
                else:
                    setattr(recipe, k, v)
            recipe.save()
            RecipeItem.objects.filter(recipe=recipe).delete()
            for item_data in items:
                # For now, just create the item without cycle checking
                # Cycle checking would be complex with the item-based approach
                RecipeItem.objects.create(
                    recipe=recipe,
                    item_id=item_data["item_id"],
                    quantity=item_data["quantity"],
                    unit=item_data["unit"],
                    loss_pct=item_data.get("loss_pct") or 0,
                    sort_order=item_data.get("sort_order") or 0,
                    notes=_strip_or_none(item_data.get("notes")),
                )
        return True, "Recipe updated."
    except Recipe.DoesNotExist:
        return False, "Recipe not found."
    except (IntegrityError, ValueError) as exc:
        logger.error("Error updating recipe: %s", exc)
        return False, str(exc)


def delete_recipe(recipe_id: int) -> Tuple[bool, str]:
    """Delete a recipe and its items."""
    try:
        with transaction.atomic():
            try:
                recipe = Recipe.objects.get(pk=recipe_id)
            except Recipe.DoesNotExist:
                return False, "Recipe not found."
            RecipeItem.objects.filter(recipe=recipe).delete()
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
    rows = (
        RecipeItem.objects.filter(recipe_id=recipe_id)
        .select_related("item")
        .values(
            "item_id",
            "item__unit_id",
            "item__is_active",
            "quantity",
            "unit",
            "loss_pct",
        )
    )
    for row in rows:
        qty = (
            multiplier
            * float(row["quantity"])
            / (1 - float(row.get("loss_pct") or 0) / 100.0)
        )

        # For now, treat all items as direct items (no sub-recipes)
        # Sub-recipe functionality can be added later if needed
        if not row["item__is_active"]:
            raise ValueError("Inactive item component encountered")
        item_unit = get_unit_display_name(row["item__unit_id"])
        if item_unit != row["unit"]:
            raise ValueError("Unit mismatch for item component")
        totals[row["item_id"]] = totals.get(row["item_id"], 0) + qty
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
        get_low_stock_items.cache_clear()
        return True, "Sale recorded."
    except Recipe.DoesNotExist:
        return False, "Recipe not found."
    except (Item.DoesNotExist, ValueError) as ve:
        logger.error("Error recording sale: %s", ve)
        return False, str(ve)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("DB error recording sale: %s", exc)
        return False, "A database error occurred during sale recording."
