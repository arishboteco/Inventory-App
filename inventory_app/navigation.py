"""Utilities for navigation links used throughout the application."""

from __future__ import annotations

import logging
from typing import Iterable, List, Mapping

from django.urls import NoReverseMatch, reverse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Central definitions of navigation sections.  Each entry contains the user
# facing title and the URL name that should resolve to the actual path.  The
# list is defined in a single place to make it easy to add or remove sections
# without having to touch multiple templates or context processors.
# ---------------------------------------------------------------------------
SECTION_DEFINITIONS: List[tuple[str, str]] = [
    ("Home", "root"),
    ("Dashboard", "dashboard"),
    ("Inventory", "items_list"),
    ("Orders", "purchase_orders_list"),
    ("Suppliers", "suppliers_list"),
    ("Reports", "history_reports"),
]

# Build the list of navigation links from the central definition above.  This
# indirection makes it trivial to auto-generate the list in the future should
# the application expose the section definition via configuration or a
# database table.
NAVIGATION_LINKS = [
    {"title": title, "url_name": url_name} for title, url_name in SECTION_DEFINITIONS
]


def _resolve_link(link: Mapping[str, str]) -> Mapping[str, str]:
    """Resolve a navigation link to its absolute URL.

    Each link dictionary must contain a ``url_name`` key which is resolved using
    :func:`django.urls.reverse`.  If the URL name cannot be resolved the error is
    logged and re-raised to surface misconfigured navigation early during
    development and tests.
    """

    try:
        url = reverse(link["url_name"])
    except NoReverseMatch:
        logger.error("Navigation link '%s' could not be reversed", link["url_name"])
        raise
    return {"title": link["title"], "url": url}


def get_navigation_links(links: Iterable[Mapping[str, str]] | None = None) -> List[dict]:
    """Build the list of navigation links with resolved URLs.

    Parameters
    ----------
    links:
        Optional iterable of navigation dictionaries.  If not provided the
        module level ``NAVIGATION_LINKS`` is used.  Providing a parameter makes
        testing and potential future auto-generation easier.
    """

    links = NAVIGATION_LINKS if links is None else list(links)
    return [_resolve_link(link) for link in links]


def primary_navigation(request):
    """Provide primary navigation links for the top navigation bar."""
    return {"primary_navigation": get_navigation_links()}

