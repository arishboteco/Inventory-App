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
# Navigation groups: title shown to the user and underlying URL names grouped
# by logical section.  Grouping navigation in a single location keeps the
# structure consistent across templates and makes it easy to add additional
# sections in the future.
NAVIGATION_GROUPS: List[tuple[str, List[Mapping[str, str]]]] = [
    (
        "Plan & Request",
        [
            {
                "title": "Item Catalog",
                "description": "Maintain products, variants, and stock policies.",
                "url_name": "items_list",
            },
            {
                "title": "Recipes & BOMs",
                "description": "Build formulations and production yields.",
                "url_name": "recipes_list",
            },
            {
                "title": "Indent Requests",
                "description": "Capture and prioritise internal demand.",
                "url_name": "indents_list",
            },
        ],
    ),
    (
        "Buy & Receive",
        [
            {
                "title": "Purchase Orders",
                "description": "Plan sourcing and track order progress.",
                "url_name": "purchase_orders_list",
            },
            {
                "title": "Goods Received Notes",
                "description": "Verify deliveries and attach supporting docs.",
                "url_name": "grn_list",
            },
            {
                "title": "Supplier Directory",
                "description": "Manage vendor contacts and statuses.",
                "url_name": "suppliers_list",
            },
        ],
    ),
    (
        "Fulfill & Track",
        [
            {
                "title": "Stock Movements",
                "description": "Review adjustments and inter-store transfers.",
                "url_name": "stock_movements",
            },
            {
                "title": "Consolidation Planner",
                "description": "Bundle approved indents into supplier orders.",
                "url_name": "indents_consolidate_preview",
            },
            {
                "title": "Inventory Explorer",
                "description": "Search items, batches, and availability.",
                "url_name": "explore",
            },
        ],
    ),
        (
            "Insights & Settings",
            [
                {
                    "title": "Operational Reports",
                    "description": "Analyse trends and audit activity.",
                    "url_name": "history_reports",
                },
                {
                    "title": "Visual Dashboards",
                    "description": "Track KPIs and live performance.",
                    "url_name": "visualizations",
                },
                {
                    "title": "ML Planner",
                    "description": "Run scenarios and predictive insights.",
                    "url_name": "ml_dashboard",
                },
                {
                    "title": "Workflow Handbook",
                    "description": "Follow the end-to-end Inventory Pro process.",
                    "url_name": "workflow_guide",
                },
            ],
        ),
]

# Flattened list of links is still exposed for convenience in tests and any
# legacy code that expects a simple sequence of links.
NAVIGATION_LINKS = [
    {
        "title": link["title"],
        "url_name": link["url_name"],
        "description": link.get("description", ""),
    }
    for _, links in NAVIGATION_GROUPS
    for link in links
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
    resolved = {"title": link["title"], "url": url, "url_name": link["url_name"]}
    description = link.get("description")
    if description:
        resolved["description"] = description
    return resolved


def get_navigation_links(
    links: Iterable[Mapping[str, str]] | None = None,
) -> List[dict]:
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


def get_navigation_groups(
    groups: Iterable[tuple[str, Iterable[tuple[str, str]]]] | None = None,
) -> List[dict]:
    """Resolve navigation groups into category dictionaries.

    Parameters
    ----------
    groups:
        Optional iterable of ``(category, links)`` tuples.  Defaults to the
        module level ``NAVIGATION_GROUPS``.  Each ``links`` entry contains
        ``(title, url_name)`` tuples which are resolved to absolute URLs.
    """

    groups = NAVIGATION_GROUPS if groups is None else list(groups)
    resolved = []
    for category, links in groups:
        link_dicts = [
            {
                "title": link["title"],
                "url_name": link["url_name"],
                "description": link.get("description", ""),
            }
            for link in links
        ]
        resolved.append(
            {"category": category, "links": get_navigation_links(link_dicts)}
        )
    return resolved


def primary_navigation(request):
    """Provide grouped navigation data for the top navigation bar."""
    return {"navigation_groups": get_navigation_groups()}
