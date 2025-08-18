"""Lightweight UI-related service helpers.

This module provides small helper functions originally from the legacy
Streamlit codebase. They avoid any Streamlit dependency so they can be
used in tests and Django views."""

from typing import Callable, Dict, Iterable, List, Mapping, Optional, Tuple, Any

import pandas as pd

__all__ = [
    "build_item_choice_label",
    "build_recipe_choice_label",
    "build_component_options",
    "autofill_component_meta",
]


def build_item_choice_label(item: Mapping) -> str:
    """Return standardized label for item choices.

    Displays ``Name (ID) | Unit | Category | On-hand``. SKU is approximated
    by ``item_id`` if an explicit SKU is unavailable.
    """

    name = item.get("name", "")
    sku = item.get("sku") or item.get("item_id")
    unit = item.get("base_unit", "")
    category = item.get("category", "")
    stock = item.get("current_stock")
    stock_part = f"{float(stock):.2f}" if isinstance(stock, (int, float)) else "?"
    return f"{name} ({sku}) | {unit} | {category} | {stock_part}"


def build_recipe_choice_label(recipe: Mapping) -> str:
    """Return standardized label for sub-recipe choices.

    Displays ``Recipe Name | Default Unit | Tags``.
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
            "base_unit": item.get("base_unit"),
            # include purchase_unit so downstream UIs can offer a choice
            # between base and purchase units when selecting component quantities
            "purchase_unit": item.get("purchase_unit"),
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


def autofill_component_meta(
    df: pd.DataFrame, choice_map: Dict[str, Dict[str, Any]]
) -> pd.DataFrame:
    """Fill the ``unit`` and ``category`` columns using ``choice_map``.

    Any row whose component label exists in ``choice_map`` receives the
    corresponding unit and category; others are set to ``None``. The
    dataframe is modified in place and returned for convenience.
    """

    if df is None or "component" not in df:
        return df
    for idx, comp in df["component"].items():
        meta = choice_map.get(comp)
        if meta:
            df.at[idx, "unit"] = meta.get("base_unit")
            df.at[idx, "category"] = meta.get("category")
        else:
            df.at[idx, "unit"] = None
            df.at[idx, "category"] = None
    return df
