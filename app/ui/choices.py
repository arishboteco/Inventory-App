"""Shared helpers for building choice labels in dropdowns."""
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Tuple

__all__ = [
    "build_item_choice_label",
    "build_recipe_choice_label",
    "build_component_options",
]

def build_item_choice_label(item: Mapping) -> str:
    """Return standardized label for item choices.

    Displays: Name (ID) | Unit | Category | On-hand
    SKU is approximated by item_id if explicit SKU is unavailable.
    """
    name = item.get("name", "")
    sku = item.get("sku") or item.get("item_id")
    unit = item.get("unit", "")
    category = item.get("category", "")
    stock = item.get("current_stock")
    stock_part = f"{float(stock):.2f}" if isinstance(stock, (int, float)) else "?"
    return f"{name} ({sku}) | {unit} | {category} | {stock_part}"


def build_recipe_choice_label(recipe: Mapping) -> str:
    """Return standardized label for sub-recipe choices.

    Displays: Recipe Name | Default Unit | Tags
    """
    name = recipe.get("name", "")
    unit = recipe.get("default_yield_unit") or ""
    tags = recipe.get("tags") or ""
    return f"{name} | {unit} | {tags}"


def build_component_options(
    items: Iterable[Mapping] = (),
    sub_recipes: Iterable[Mapping] = (),
    *,
    placeholder: Optional[str] = None,
    item_filter: Optional[Callable[[Mapping], bool]] = None,
    recipe_filter: Optional[Callable[[Mapping], bool]] = None,
) -> Tuple[List[str], Dict[str, Dict]]:
    """Return option labels and metadata map for items and sub-recipes.

    Parameters
    ----------
    items : Iterable[Mapping]
        Iterable of item-like mappings.
    sub_recipes : Iterable[Mapping]
        Iterable of sub-recipe mappings.
    placeholder : str, optional
        If provided, inserted at the start of the options list.
    item_filter : Callable[[Mapping], bool], optional
        Function returning True for items to include.
    recipe_filter : Callable[[Mapping], bool], optional
        Function returning True for recipes to include.

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
        if item_filter and not item_filter(item):
            continue
        label = build_item_choice_label(item)
        meta_map[label] = {
            "kind": "ITEM",
            "id": int(item.get("item_id")),
            "unit": item.get("unit"),
            "category": item.get("category"),
            "name": item.get("name"),
        }
        options.append(label)

    for recipe in sub_recipes or []:
        if recipe_filter and not recipe_filter(recipe):
            continue
        label = build_recipe_choice_label(recipe)
        meta_map[label] = {
            "kind": "RECIPE",
            "id": int(recipe.get("recipe_id")),
            "unit": recipe.get("default_yield_unit"),
            "category": "Sub-recipe",
            "name": recipe.get("name"),
        }
        options.append(label)

    return options, meta_map
