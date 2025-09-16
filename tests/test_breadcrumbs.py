import pytest
from django.template.loader import render_to_string
from django.urls import reverse


def test_breadcrumb_renders_full_trail():
    context = {
        "list_title": "Purchase Orders",
        "list_url": reverse("purchase_orders_list"),
        "current_title": "PO 10",
    }
    html = render_to_string("components/breadcrumb.html", context)
    assert "Home" in html
    assert "Purchase Orders" in html
    assert "PO 10" in html
    assert reverse("purchase_orders_list") in html


def test_breadcrumb_as_text_when_missing_url():
    context = {
        "list_title": "Operational Reports",
        "current_title": "Inventory Turns",
    }
    html = render_to_string("components/breadcrumb.html", context)
    assert "Operational Reports" in html
    assert "Inventory Turns" in html
    assert "Operational Reports</a>" not in html


@pytest.mark.parametrize(
    "context",
    [
        {},
        {"list_title": ""},
        {"current_title": ""},
    ],
)
def test_breadcrumb_hidden_without_titles(context):
    html = render_to_string("components/breadcrumb.html", context)
    assert html.strip() == ""
