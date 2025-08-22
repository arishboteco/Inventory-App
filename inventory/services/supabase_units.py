import logging
import os
import time
from typing import Dict, List

try:
    from supabase import Client, create_client
except Exception:  # pragma: no cover - supabase optional
    Client = None  # type: ignore
    create_client = None  # type: ignore


logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # seconds
_cache: Dict[str, List[str]] | None = None
_cache_time: float | None = None


def _load_units_from_supabase() -> Dict[str, List[str]]:
    """Fetch units mapping from the Supabase ``units`` table.

    Returns a mapping of base units to a list of compatible purchase units. If
    the Supabase client cannot be initialised or the request fails, an empty
    mapping is returned.
    """

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key or create_client is None:
        logger.warning("Supabase is not configured; no units loaded")
        return {}
    try:  # pragma: no cover - network interaction
        client: Client = create_client(url, key)
        # The ``units`` table contains a ``name`` column for the base unit and
        # a ``purchase_units`` column with a list of compatible units.
        resp = client.table("units").select("name,purchase_units").execute()
        data = resp.data or []
    except Exception as exc:
        logger.warning("Failed to fetch units from Supabase: %s", exc)
        return {}

    units: Dict[str, List[str]] = {}
    for row in data:
        name = row.get("name")
        purchase = row.get("purchase_units") or []
        if isinstance(purchase, str):
            purchase = [purchase]
        if name:
            units[name] = purchase
    return units


def get_units(force: bool = False) -> Dict[str, List[str]]:
    """Return cached units mapping, refreshing from Supabase if expired."""
    global _cache, _cache_time
    now = time.time()
    if (
        not force
        and _cache is not None
        and _cache_time is not None
        and now - _cache_time < _CACHE_TTL
    ):
        return _cache

    _cache = _load_units_from_supabase()
    _cache_time = now
    return _cache

