"""Shared helpers for building choice labels in dropdowns."""
from typing import Mapping

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
