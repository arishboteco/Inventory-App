NAVIGATION_LINKS = [
    {"title": "Dashboard", "url_name": "dashboard"},
    {"title": "Inventory", "url_name": "items_list"},
    {"title": "Orders", "url_name": "purchase_orders_list"},
    {"title": "Suppliers", "url_name": "suppliers_list"},
    {"title": "Reports", "url_name": "history_reports"},
]


def primary_navigation(request):
    """Provide primary navigation links for the top navigation bar."""
    return {"primary_navigation": NAVIGATION_LINKS}
