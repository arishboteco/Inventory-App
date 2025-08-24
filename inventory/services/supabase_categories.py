import logging
from typing import Dict, List, Optional

from .supabase_client import SupabaseException, get_supabase_client
from .supabase_cache import get_cached


logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # seconds


def _load_categories_from_supabase() -> Dict[Optional[str], List[dict]]:
    """Fetch categories mapping from the Supabase ``category`` table.

    Returns a mapping of category names to lists of subcategories. Top level
    categories are stored under the ``None`` key. Each entry in the mapping is a
    dict containing ``id`` and ``name`` keys. If the Supabase client cannot be
    initialised or the request fails, an empty mapping is returned.
    """

    client = get_supabase_client()
    if client is None:
        logger.warning("Supabase is not configured; no categories loaded")
        return {}
    try:  # pragma: no cover - network interaction
        resp = (
            client.table("category")
            .select("category_id,category,sub_category")
            .execute()
        )
    except SupabaseException:  # pragma: no cover - network interaction
        logger.exception("Failed to fetch categories from Supabase")
        return {}

    cats: Dict[Optional[str], List[dict]] = {}
    top_seen: set[str] = set()
    child_seen: Dict[str, set[str]] = {}

    for row in resp.data or []:
        cat_id = row.get("category_id")
        cat_name = row.get("category")
        sub_name = row.get("sub_category")

        if cat_id is not None and cat_name:
            if cat_name not in top_seen:
                cats.setdefault(None, []).append({"id": cat_id, "name": cat_name})
                top_seen.add(cat_name)

            if sub_name:
                seen = child_seen.setdefault(cat_name, set())
                if sub_name not in seen:
                    cats.setdefault(cat_name, []).append(
                        {"id": cat_id, "name": sub_name}
                    )
                    seen.add(sub_name)

    for children in cats.values():
        children.sort(key=lambda c: c["name"])
    return cats


get_categories = get_cached(lambda: _load_categories_from_supabase(), _CACHE_TTL)
get_categories.__doc__ = (
    "Return cached categories mapping, refreshing from Supabase if expired."
)
