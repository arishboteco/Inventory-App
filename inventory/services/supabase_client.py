import logging
import os
from typing import Optional

try:
    from supabase import Client, SupabaseException, create_client
except ModuleNotFoundError:  # pragma: no cover - supabase optional
    Client = None  # type: ignore
    create_client = None  # type: ignore

    class SupabaseException(Exception):
        pass

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_supabase_client() -> Optional[Client]:
    """Return a cached Supabase client if available.

    The client is initialised using the ``SUPABASE_URL`` and ``SUPABASE_KEY``
    environment variables. If configuration is missing or the connection
    fails, ``None`` is returned and the error is logged. The initialisation
    is performed once and the resulting client is cached for subsequent
    calls.
    """

    global _client
    if _client is not None:
        return _client

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
