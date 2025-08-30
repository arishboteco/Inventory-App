import pytest
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse


@pytest.mark.django_db
def test_top_nav_template_contains_links(django_user_model):
    user = django_user_model.objects.create_user(username="u", password="pw")
    rf = RequestFactory()
    request = rf.get("/")
    request.user = user
    html = render_to_string("components/top_nav.html", request=request)
    expected = [
        "Dashboard",
        "Inventory",
        "Orders",
        "Suppliers",
        "Reports",
    ]
    for text in expected:
        assert text in html


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name,current_title",
    [
        ("dashboard", "Dashboard"),
        ("items_list", "Inventory"),
        ("purchase_orders_list", "Orders"),
        ("suppliers_list", "Suppliers"),
        ("history_reports", "Reports"),
    ],
)
def test_pages_render_nav_and_breadcrumb(client, django_user_model, url_name, current_title):
    user = django_user_model.objects.create_user(username="u", password="pw")
    client.force_login(user)
    resp = client.get(reverse(url_name))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "<nav" in html
    assert "flex items-center gap-1 text-sm text-gray-500 mb-4" in html
    assert current_title in html


@pytest.mark.django_db
def test_home_page_contains_nav_links(client, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="pw")
    client.force_login(user)
    resp = client.get(reverse("root"))
    html = resp.content.decode()
    expected = [
        "Dashboard",
        "Inventory",
        "Orders",
        "Suppliers",
        "Reports",
    ]
    for text in expected:
        assert text in html
