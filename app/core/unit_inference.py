"""Utility to infer sensible units for items.

This module provides a small heuristic function :func:`infer_units` which tries
to guess an item's base unit and optional purchase unit from its name or
category.  The goal is not to be perfect but to offer sensible defaults so that
users can add items quickly without having to manually specify units every
single time.

The implementation intentionally keeps things lightweight – a couple of keyword
lookups and fallbacks – so that it remains fast and free from heavy ML
dependencies.
"""
from __future__ import annotations

from typing import Dict, Tuple, Optional

# Maps a keyword found in the *item name* to a tuple of (base_unit, purchase_unit)
_NAME_KEYWORD_MAP: Dict[str, Tuple[str, Optional[str]]] = {
    # Liquids
    "milk": ("ltr", "carton"),
    "water": ("ltr", "bottle"),
    "oil": ("ltr", "bottle"),
    # Dry goods
    "flour": ("kg", "bag"),
    "rice": ("kg", "bag"),
    "sugar": ("kg", "bag"),
    # Proteins / others
    "egg": ("pcs", "dozen"),
    "bread": ("pcs", "loaf"),
    "apple": ("kg", "crate"),
}

# Fallback mapping based purely on *category* if no keyword matched.
_CATEGORY_DEFAULT_MAP: Dict[str, Tuple[str, Optional[str]]] = {
    "dairy": ("ltr", "carton"),
    "beverage": ("ltr", "bottle"),
    "beverages": ("ltr", "bottle"),
    "produce": ("kg", None),
    "vegetable": ("kg", None),
    "vegetables": ("kg", None),
    "baking": ("kg", "bag"),
    "bakery": ("pcs", "loaf"),
}


def infer_units(name: str, category: str | None) -> tuple[str, str | None]:
    """Infer base and purchase units for an item.

    Parameters
    ----------
    name:
        The name of the item. Keyword heuristics are applied on the lowercase
        name.
    category:
        Optional category for the item. Used as a secondary signal when the
        name alone is not sufficient.

    Returns
    -------
    tuple[str, str | None]
        A tuple containing the inferred base unit and, if applicable, the
        purchase unit.  If no specific match is found, defaults to ``("pcs",
        None)``.
    """

    name_l = (name or "").lower()
    category_l = (category or "").lower()

    for keyword, units in _NAME_KEYWORD_MAP.items():
        if keyword in name_l:
            return units

    for cat, units in _CATEGORY_DEFAULT_MAP.items():
        if category_l == cat:
            return units

    # Generic fallback – assume individual pieces with no purchase unit.
    return "pcs", None
