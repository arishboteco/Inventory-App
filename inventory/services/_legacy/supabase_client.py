import logging
import os
from typing import Any, Optional

try:
    from supabase import Client, SupabaseException, create_client
except ModuleNotFoundError:  # pragma: no cover - supabase optional
    Client = None  # type: ignore
    create_client = None  # type: ignore

    class SupabaseException(Exception):
        pass


logger = logging.getLogger(__name__)

_client: Optional[Any] = None


def _legacy_enabled() -> bool:
    """Return True if legacy Supabase integration is enabled.

    Controlled by LEGACY_SUPABASE env var (default enabled).
    Set to false/0/off to disable.
    """
    val = (os.getenv("LEGACY_SUPABASE") or "").strip().lower()
    if val in {"0", "false", "no", "off"}:
        return False
    return True


def get_supabase_client() -> Optional[Any]:
    """Return a cached Supabase client if available or enabled."""
    global _client
    if _client is not None:
        return _client

    if not _legacy_enabled():
        logger.info("Legacy Supabase integration disabled (LEGACY_SUPABASE)")
        return None

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key or create_client is None:
        logger.warning("Supabase is not configured")
        return None
    try:  # pragma: no cover - network interaction
        _client = create_client(url, key)
    except SupabaseException:  # pragma: no cover - network interaction
        logger.exception("Failed to initialise Supabase client")
        return None
    return _client
