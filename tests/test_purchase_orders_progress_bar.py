from types import SimpleNamespace

from django.template.loader import render_to_string


def test_purchase_order_progress_bar_renders_width():
    po = SimpleNamespace(
        pk=1,
        supplier=SimpleNamespace(name="ACME"),
        order_date="2023-01-01",
        badge_class="status-open",
        get_status_display=lambda: "Open",
        progress_percent=42,
        received_total=0,
        ordered_total=0,
    )
    page_obj = SimpleNamespace(
        has_previous=False,
        has_next=False,
        number=1,
        paginator=SimpleNamespace(num_pages=1, page_range=[1]),
    )
    html = render_to_string(
        "inventory/purchase_orders/_table.html",
        {"orders": [po], "page_obj": page_obj, "querystring": ""},
    )
    assert 'style="width: 42%"' in html
    assert "--progress" not in html
