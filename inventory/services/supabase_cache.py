"""Generic caching utilities for Supabase-backed services.

This module provides a small helper to wrap data-fetching callables with
thread-safe caching and time-based invalidation. It centralises the
previously duplicated cache and lock management used by several Supabase
service modules.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

logger = logging.getLogger(__name__)


T = TypeVar("T")


@dataclass
class _CacheState(Generic[T]):
    """Internal mutable cache container used by ``get_cached``."""

    value: T | None = None
    time: float | None = None


def get_cached(fetch_func: Callable[[], T], ttl: int) -> Callable[[bool], T]:
    """Return a callable that caches ``fetch_func`` results for ``ttl`` seconds.

    The returned function accepts a ``force`` boolean parameter. When ``force``
    is ``True`` the cache is bypassed and refreshed immediately. Cache state and
    the internal lock are exposed via ``_state`` and ``_lock`` attributes to aid
    testing.
    """

    lock = threading.Lock()
    state: _CacheState[T] = _CacheState()

    def wrapper(force: bool = False) -> T:
        with lock:
            now = time.time()
            if (
                not force
                and state.value is not None
                and state.time is not None
                and now - state.time < ttl
            ):
                return state.value

            try:
                state.value = fetch_func()
            except Exception:
                if state.value is not None:
                    logger.exception("Failed to refresh cached value")
                    return state.value
                raise
            state.time = now
            return state.value

    wrapper._state = state  # type: ignore[attr-defined]
    wrapper._lock = lock  # type: ignore[attr-defined]
    return wrapper


__all__ = ["get_cached"]
