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
        "Insights",
        [
            {
                "title": "Overview",
                "description": "Live stock overview, KPIs, and trend charts.",
                "url_name": "root",
            },
            {
                "title": "Food Cost",
                "description": "Recipe costs, margins, and selling prices.",
                "url_name": "food_cost_report",
            },
            {
                "title": "History",
                "description": "Past stock activity and audit trail.",
                "url_name": "history_reports",
            },
            {
                "title": "Stock Charts",
                "description": "Interactive stock trend chart with filters.",
                "url_name": "visualizations",
            },
            {
                "title": "Reorder Suggestions",
                "description": "What to order based on usage patterns.",
                "url_name": "ml_dashboard",
            },
        ],
    ),
    (
        "Procurement",
        [
            {
                "title": "Indents",
                "description": "Raise requests for items you need.",
                "url_name": "indents_list",
            },
            {
                "title": "Order Planner",
                "description": "Combine indents into purchase orders.",
                "url_name": "indents_consolidate_preview",
            },
            {
                "title": "Purchase Orders",
                "description": "Orders sent to suppliers.",
                "url_name": "purchase_orders_list",
            },
            {
                "title": "Receiving",
                "description": "Check in deliveries from suppliers.",
                "url_name": "grn_list",
            },
        ],
    ),
    (
        "Stock",
        [
            {
                "title": "Movements",
                "description": "Transfers, wastage, and adjustments.",
                "url_name": "stock_movements",
            },
            {
                "title": "Stock Count",
                "description": "Physical count and fix differences.",
                "url_name": "stock_take_list",
            },
        ],
    ),
    (
        "Master Data",
        [
            {
                "title": "Items",
                "description": "Your products, stock levels, and settings.",
                "url_name": "items_list",
            },
            {
                "title": "Recipes",
                "description": "Ingredients, portions, and costings.",
                "url_name": "recipes_list",
            },
            {
                "title": "Suppliers",
                "description": "Who you buy from.",
                "url_name": "suppliers_list",
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
    """Provide grouped navigation data and notification counts for the top nav."""
    ctx = {"navigation_groups": get_navigation_groups()}
    if hasattr(request, "user") and request.user.is_authenticated:
        try:
            from inventory.services import kpis

            low = kpis.low_stock_count()
            pending = sum(kpis.pending_indent_counts().values())
            notifications = []
            if pending > 0:
                noun = "indent" if pending == 1 else "indents"
                notifications.append(
                    {
                        "text": f"{pending} {noun} awaiting approval",
                        "url": "/indents/?status=PENDING",
                    }
                )
            if low > 0:
                noun = "item" if low == 1 else "items"
                notifications.append(
                    {
                        "text": f"{low} {noun} below reorder level",
                        "url": "/items/?stock_status=low",
                    }
                )
                notifications.append(
                    {
                        "text": f"Generate indent for {low} low-stock {noun}",
                        "url": "/indents/generate-from-low-stock/",
                    }
                )
            ctx["notification_count"] = low + pending
            ctx["notifications"] = notifications
        except Exception:
            ctx["notification_count"] = 0
            ctx["notifications"] = []
    else:
        ctx["notification_count"] = 0
        ctx["notifications"] = []
    return ctx
