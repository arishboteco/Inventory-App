"""Utilities for navigation links used throughout the application."""

from __future__ import annotations

import logging
from typing import Iterable, List, Mapping

from django.urls import NoReverseMatch, reverse

logger = logging.getLogger(__name__)

ROLE_OWNER = "owner"
ROLE_PURCHASE = "purchase"
ROLE_STOREKEEPER = "storekeeper"
ROLE_HEAD_CHEF = "head_chef"
ROLE_KITCHEN_STAFF = "kitchen_staff"

ROLE_GROUP_NAME_MAP: Mapping[str, str] = {
    ROLE_OWNER: "Owner",
    ROLE_PURCHASE: "Purchase",
    ROLE_STOREKEEPER: "Storekeeper",
    ROLE_HEAD_CHEF: "Head Chef",
    ROLE_KITCHEN_STAFF: "Kitchen Staff",
}

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
                "title": "Savings Ledger",
                "description": "Trace estimated, confirmed, and lost savings.",
                "url_name": "savings_ledger_list",
            },
            {
                "title": "Recovery Actions",
                "description": "Track assigned actions and verified recovery.",
                "url_name": "recovery_actions_list",
            },
            {
                "title": "Sales Import",
                "description": "Import POS sales and map menu items to recipes.",
                "url_name": "pos_sales_import",
            },
            {
                "title": "Ideal vs Actual",
                "description": "Track item-level variance and leakage value by period.",
                "url_name": "variance_report",
            },
            {
                "title": "Chef Bulletins",
                "description": "Recipe alerts, trials, and chef decisions.",
                "url_name": "chef_bulletins_list",
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
            {
                "title": "Vendor Prices",
                "description": "Compare item prices across approved vendors.",
                "url_name": "vendor_prices_list",
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

ROLE_ALLOWED_URLS: Mapping[str, set[str]] = {
    ROLE_OWNER: {
        "root",
        "food_cost_report",
        "savings_ledger_list",
        "history_reports",
        "visualizations",
        "ml_dashboard",
        "pos_sales_import",
        "variance_report",
        "chef_bulletins_list",
        "indents_consolidate_preview",
        "purchase_orders_list",
        "grn_list",
        "vendor_prices_list",
        "recovery_actions_list",
    },
    ROLE_PURCHASE: {
        "indents_consolidate_preview",
        "vendor_prices_list",
        "purchase_orders_list",
        "grn_list",
        "savings_ledger_list",
        "recovery_actions_list",
    },
    ROLE_STOREKEEPER: {
        "grn_list",
        "stock_movements",
        "stock_take_list",
        "items_list",
    },
    ROLE_HEAD_CHEF: {
        "food_cost_report",
        "recipes_list",
        "stock_movements",
        "ml_dashboard",
        "pos_sales_import",
        "variance_report",
        "chef_bulletins_list",
        "recovery_actions_list",
    },
    ROLE_KITCHEN_STAFF: {
        "indents_list",
    },
}


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


def get_primary_role(user) -> str | None:
    """Return the first recognized role from the user's Django groups."""
    if not getattr(user, "is_authenticated", False):
        return None
    if getattr(user, "is_superuser", False):
        return ROLE_OWNER
    names = set(user.groups.values_list("name", flat=True))
    normalized = {name.strip().lower() for name in names}
    for role_key, group_name in ROLE_GROUP_NAME_MAP.items():
        if group_name.lower() in normalized:
            return role_key
    return None


def get_navigation_groups_for_role(role: str | None) -> List[dict]:
    """Return navigation groups filtered by role, or full groups if no role."""
    if role == ROLE_OWNER:
        return get_navigation_groups()
    allowed_urls = ROLE_ALLOWED_URLS.get(role)
    if not allowed_urls:
        return get_navigation_groups()
    scoped_groups: List[tuple[str, List[Mapping[str, str]]]] = []
    for category, links in NAVIGATION_GROUPS:
        filtered_links = [
            link for link in links if link.get("url_name", "") in allowed_urls
        ]
        if filtered_links:
            scoped_groups.append((category, filtered_links))
    return get_navigation_groups(groups=scoped_groups)


def primary_navigation(request):
    """Provide grouped navigation data and notification counts for the top nav."""
    match = getattr(request, "resolver_match", None)
    url_name = getattr(match, "url_name", "") or ""
    path = getattr(request, "path", "") or ""
    if (
        request.headers.get("HX-Request")
        or url_name.endswith("_table")
        or url_name.endswith("_cards")
        or "/table/" in path
        or "/cards/" in path
    ):
        return {
            "navigation_groups": [],
            "notification_count": 0,
            "notifications": [],
        }
    user = getattr(request, "user", None)
    role = get_primary_role(user)
    ctx = {
        "navigation_groups": get_navigation_groups_for_role(role),
        "primary_role": role,
    }
    if hasattr(request, "user") and request.user.is_authenticated:
        try:
            from inventory.services.nav_kpis import get_cached_nav_kpis

            nav_k = get_cached_nav_kpis()
            low = nav_k["low_stock"]
            pending = nav_k["pending_total"]
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
