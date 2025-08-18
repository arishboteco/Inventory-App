"""Lightweight UI-related service helpers.

This module provides small helper functions originally from the legacy
Streamlit codebase. They avoid any Streamlit dependency so they can be
used in tests and Django views."""

from typing import Callable, Dict, Iterable, List, Mapping, Optional, Tuple, Any

__all__ = [
    "build_item_choice_label",
    "build_recipe_choice_label",
    "build_component_options",
    "autofill_component_meta",
]


def _to_dict(obj: Any) -> Dict[str, Any]:
    """Return a dictionary representation of ``obj``.

    Supports plain mappings, objects with ``model_dump``/``dict`` methods
    (e.g., pydantic models) and simple attribute containers. The function is
    intentionally lightweight to avoid adding hard dependencies.
    """

    if isinstance(obj, Mapping):
        return dict(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()  # type: ignore[no-any-return]
    if hasattr(obj, "dict"):
        return obj.dict()  # type: ignore[no-any-return]
    return {k: getattr(obj, k) for k in dir(obj) if not k.startswith("_")}


def build_item_choice_label(item: Any) -> str:
    """Return standardized label for item choices.

    Displays ``Name (ID) | Unit | Category | On-hand``. SKU is approximated
    by ``item_id`` if an explicit SKU is unavailable. ``item`` may be a plain
    mapping, a Pydantic model, or any object with compatible attributes.
    """

    item = _to_dict(item)
    name = item.get("name", "")
    sku = item.get("sku") or item.get("item_id")
    unit = item.get("base_unit", "")
    category = item.get("category", "")
    stock = item.get("current_stock")
    stock_part = f"{float(stock):.2f}" if isinstance(stock, (int, float)) else "?"
    return f"{name} ({sku}) | {unit} | {category} | {stock_part}"


def build_recipe_choice_label(recipe: Any) -> str:
    """Return standardized label for sub-recipe choices.

    Displays ``Recipe Name | Default Unit | Tags``. ``recipe`` may be a plain
    mapping, a Pydantic model, or any object with compatible attributes.
    """

    recipe = _to_dict(recipe)
    name = recipe.get("name", "")
    unit = recipe.get("default_yield_unit") or ""
    tags = recipe.get("tags") or ""
    return f"{name} | {unit} | {tags}"


def build_component_options(
    items: Iterable[Any] = (),
    sub_recipes: Iterable[Any] = (),
    *,
    placeholder: Optional[str] = None,
    item_filter: Optional[Callable[[Mapping], bool]] = None,
    recipe_filter: Optional[Callable[[Mapping], bool]] = None,
) -> Tuple[List[str], Dict[str, Dict]]:
    """Return option labels and metadata map for items and sub-recipes.

    ``items`` and ``sub_recipes`` may contain dicts, Pydantic models or other
    attribute-based objects. Filters receive a plain dict representation of
    each object if provided.

    Returns
    -------
    Tuple[List[str], Dict[str, Dict]]
        A tuple of option labels and a metadata mapping keyed by label.
    """

    options: List[str] = []
    meta_map: Dict[str, Dict] = {}

    if placeholder is not None:
        options.append(placeholder)

    for item in items or []:
        item_dict = _to_dict(item)
        if item_filter and not item_filter(item_dict):
            continue
        label = build_item_choice_label(item_dict)
        meta_map[label] = {
            "kind": "ITEM",
            "id": int(item_dict.get("item_id")),
            "base_unit": item_dict.get("base_unit"),
            # include purchase_unit so downstream UIs can offer a choice
            # between base and purchase units when selecting component quantities
            "purchase_unit": item_dict.get("purchase_unit"),
            "category": item_dict.get("category"),
            "name": item_dict.get("name"),
        }
        options.append(label)

    for recipe in sub_recipes or []:
        recipe_dict = _to_dict(recipe)
        if recipe_filter and not recipe_filter(recipe_dict):
            continue
        label = build_recipe_choice_label(recipe_dict)
        meta_map[label] = {
            "kind": "RECIPE",
            "id": int(recipe_dict.get("recipe_id")),
            "unit": recipe_dict.get("default_yield_unit"),
            "category": "Sub-recipe",
            "name": recipe_dict.get("name"),
        }
        options.append(label)

    return options, meta_map


def autofill_component_meta(
    rows: Iterable[Any], choice_map: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Fill the ``unit`` and ``category`` fields using ``choice_map``.

    ``rows`` may contain dictionaries, Pydantic models or simple objects.
    Each row is converted to a dict, updated in place, and returned. Any row
    whose component label exists in ``choice_map`` receives the corresponding
    unit and category; others are set to ``None``.
    """

    result = [_to_dict(row) for row in rows or []]
    for row in result:
        meta = choice_map.get(row.get("component"))
        if meta:
            row["unit"] = meta.get("base_unit")
            row["category"] = meta.get("category")
        else:
            row["unit"] = None
            row["category"] = None
    return result
