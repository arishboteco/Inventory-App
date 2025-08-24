import logging
from typing import Dict, List

from .supabase_client import SupabaseException, get_supabase_client
from .supabase_cache import get_cached


logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # seconds


def _load_units_from_supabase() -> Dict[str, List[str]]:
    """Fetch units mapping from the Supabase ``units`` table.

    Returns a mapping of base units to a list of compatible purchase units. If
    the Supabase client cannot be initialised or the request fails, an empty
    mapping is returned.
    """

    client = get_supabase_client()
    if client is None:
        logger.warning("Supabase is not configured; no units loaded")
        return {}
    try:  # pragma: no cover - network interaction
        resp = client.table("units").select("base_unit,purchase_unit").execute()
    except SupabaseException:  # pragma: no cover - network interaction
        logger.exception("Failed to fetch units from Supabase")
        return {}

    units: Dict[str, set[str]] = {}
    for row in resp.data or []:
        base = row.get("base_unit")
        purchase = row.get("purchase_unit")
        if not base:
            continue
        options = units.setdefault(base, set())
        if purchase:
            options.add(purchase)

    # Always allow the base unit itself as a purchase unit
    # and return sorted lists of unique options
    return {
        base: [base] + sorted(opt for opt in options if opt != base)
        for base, options in units.items()
    }


get_units = get_cached(lambda: _load_units_from_supabase(), _CACHE_TTL)
get_units.__doc__ = (
    "Return cached units mapping, refreshing from Supabase if expired."
)
