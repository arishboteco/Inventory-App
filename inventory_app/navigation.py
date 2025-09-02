"""Utilities for navigation links used throughout the application."""

from typing import List

from django.urls import NoReverseMatch, reverse


# Definitions of navigation links by URL name. The actual URLs are resolved
# dynamically to ensure that any changes to URL patterns are detected at run
# time.
NAVIGATION_LINKS = [
    {"title": "Home", "url_name": "root"},
    {"title": "Dashboard", "url_name": "dashboard"},
    {"title": "Inventory", "url_name": "items_list"},
    {"title": "Orders", "url_name": "purchase_orders_list"},
    {"title": "Suppliers", "url_name": "suppliers_list"},
    {"title": "Reports", "url_name": "history_reports"},
]


def get_navigation_links() -> List[dict]:
    """Build the list of navigation links with resolved URLs.

    Any links that reference a URL pattern that does not exist are skipped to
    prevent broken navigation entries.
    """

    resolved_links = []
    for link in NAVIGATION_LINKS:
        try:
            url = reverse(link["url_name"])
        except NoReverseMatch:
            # Ignore links that point to missing routes
            continue
        resolved_links.append({"title": link["title"], "url": url})
    return resolved_links


def primary_navigation(request):
    """Provide primary navigation links for the top navigation bar."""
    return {"primary_navigation": get_navigation_links()}
