import re
from typing import Optional, Tuple

from .supabase_units import get_units


def suggest_units(name: str) -> Tuple[Optional[str], Optional[str]]:
    """Suggest base and purchase units for an item name.

    The function tokenises ``name`` and attempts to match tokens against the
    Supabase ``units`` mapping fetched via :func:`get_units`. If a token matches
    a base unit directly it is returned along with a purchase unit (if any token
    matches the available purchase units). If only a purchase unit token is
    found the corresponding base unit is inferred.

    Parameters
    ----------
    name:
        Item name to analyse.

    Returns
    -------
    tuple[Optional[str], Optional[str]]
        Suggested ``(base_unit, purchase_unit)`` pair. ``None`` values are
        returned when no suggestion could be determined.
    """

    units_map = get_units()
    if not name:
        return None, None

    tokens = [t.lower() for t in re.split(r"\W+", name) if t]
    base: Optional[str] = None
    purchase: Optional[str] = None

    for token in tokens:
        if token in units_map:
            base = token
            break

    if base:
        purchase_options = units_map.get(base, [])
        for token in tokens:
            if token in purchase_options:
                purchase = token
                break
        if not purchase and purchase_options:
            purchase = purchase_options[0]
        return base, purchase

    for candidate_base, purchase_options in units_map.items():
        for token in tokens:
            if token in purchase_options:
                return candidate_base, token

    return None, None
