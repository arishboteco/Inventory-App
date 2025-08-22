import logging
import os
import time
from typing import Dict, List, Optional
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
_cache: Dict[Optional[int], List[dict]] | None = None
_cache_time: float | None = None
_lock = threading.Lock()


def _load_categories_from_supabase() -> Dict[Optional[int], List[dict]]:
    """Fetch categories mapping from the Supabase ``category`` table.

    Returns a mapping of parent category IDs to a list of child categories.
    ``None`` is used for top level categories. Each category is represented as a
    dict containing ``id`` and ``name`` keys.
    If the Supabase client cannot be initialised or the request fails, an empty
    mapping is returned.
    """

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key or create_client is None:
        logger.warning("Supabase is not configured; no categories loaded")
        return {}
    try:  # pragma: no cover - network interaction
        client: Client = create_client(url, key)
        resp = client.table("category").select("id,name,parent_id").execute()
    except SupabaseException:  # pragma: no cover - network interaction
        logger.exception("Failed to fetch categories from Supabase")
        return {}

    cats: Dict[Optional[int], List[dict]] = {}
    for row in resp.data or []:
        cid = row.get("id")
        name = row.get("name")
        parent = row.get("parent_id")
        if cid is None or not name:
            continue
        entry = {"id": cid, "name": name}
        cats.setdefault(parent, []).append(entry)

    for children in cats.values():
        children.sort(key=lambda c: c["name"])
    return cats


def get_categories(force: bool = False) -> Dict[Optional[int], List[dict]]:
    """Return cached categories mapping, refreshing from Supabase if expired."""
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

        _cache = _load_categories_from_supabase()
        _cache_time = now
        return _cache
