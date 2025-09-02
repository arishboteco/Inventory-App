import pytest
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import NoReverseMatch, reverse
import inventory_app.navigation as navigation


@pytest.mark.django_db
def test_top_nav_template_contains_links(django_user_model):
    user = django_user_model.objects.create_user(username="u", password="pw")
    rf = RequestFactory()
    request = rf.get("/")
    request.user = user
    html = render_to_string("components/top_nav.html", request=request)
    expected = [
        "Home",
        "Dashboard",
        "Inventory",
        "Orders",
        "Suppliers",
        "Reports",
    ]
    for text in expected:
        assert text in html
    assert f'href="{reverse("root")}"' in html


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
def test_pages_render_nav(client, django_user_model, url_name, current_title):
    user = django_user_model.objects.create_user(username="u", password="pw")
    client.force_login(user)
    resp = client.get(reverse(url_name))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "<nav" in html
    assert current_title in html


@pytest.mark.django_db
def test_home_page_contains_nav_links(client, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="pw")
    client.force_login(user)
    resp = client.get(reverse("root"))
    html = resp.content.decode()
    expected = [
        "Home",
        "Dashboard",
        "Inventory",
        "Orders",
        "Suppliers",
        "Reports",
    ]
    for text in expected:
        assert text in html


def test_navigation_links_resolve():
    """Every defined navigation link should resolve to a valid URL."""
    links = navigation.get_navigation_links()
    assert len(links) == len(navigation.NAVIGATION_LINKS)
    for original, resolved in zip(navigation.NAVIGATION_LINKS, links):
        assert resolved["url"] == reverse(original["url_name"])


def test_get_navigation_links_raises_for_missing(monkeypatch):
    """The helper should raise if an invalid URL name is supplied."""
    bad_links = navigation.NAVIGATION_LINKS + [{"title": "Bad", "url_name": "does_not_exist"}]
    monkeypatch.setattr(navigation, "NAVIGATION_LINKS", bad_links)
    with pytest.raises(NoReverseMatch):
        navigation.get_navigation_links()
