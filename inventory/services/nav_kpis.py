"""Cached top-nav notification counts (low stock + pending indents)."""

from __future__ import annotations

from typing import Any, Dict

from django.conf import settings
from django.core.cache import cache

from inventory.services import kpis

NAV_KPIS_CACHE_KEY = "nav_kpis:v1"
NAV_KPIS_TTL_SECONDS = 30


def _compute_nav_kpis() -> Dict[str, Any]:
    counts = kpis.pending_indent_counts()
    return {
        "pending_total": sum(counts.values()),
        "low_stock": kpis.low_stock_count(),
    }


def get_cached_nav_kpis() -> Dict[str, Any]:
    if getattr(settings, "DISABLE_NAV_KPIS_CACHE", False):
        return _compute_nav_kpis()
    return cache.get_or_set(NAV_KPIS_CACHE_KEY, _compute_nav_kpis, NAV_KPIS_TTL_SECONDS)
