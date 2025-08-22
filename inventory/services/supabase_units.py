import logging
import os
import time
from typing import Dict, List
import threading

try:
    from supabase import Client, create_client, SupabaseException
except ModuleNotFoundError:  # pragma: no cover - supabase optional
    Client = None  # type: ignore
    create_client = None  # type: ignore

    class SupabaseException(Exception):
        pass


logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # seconds
_cache: Dict[str, List[str]] | None = None
_cache_time: float | None = None
_lock = threading.Lock()


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
        resp = client.table("units").select("base_unit,purchase_unit").execute()
    except SupabaseException:  # pragma: no cover - network interaction
        logger.exception("Failed to fetch units from Supabase")
        return {}

    units: Dict[str, List[str]] = {}
    for row in resp.data or []:
        base = row.get("base_unit")
        purchase = row.get("purchase_unit")
        if base and purchase:
            units.setdefault(base, []).append(purchase)
    return units


def get_units(force: bool = False) -> Dict[str, List[str]]:
    """Return cached units mapping, refreshing from Supabase if expired."""
    global _cache, _cache_time
    with _lock:
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
