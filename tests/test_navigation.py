import pytest
from django.contrib.auth.models import Group
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
    groups = navigation.get_navigation_groups()
    for group in groups:
        assert group["category"] in html
        for link in group["links"]:
            assert link["title"] in html
    assert f'href="{reverse("root")}"' in html


@pytest.mark.django_db
@pytest.mark.parametrize("link", navigation.NAVIGATION_LINKS)
def test_pages_render_nav(client, django_user_model, link):
    user = django_user_model.objects.create_user(username="u", password="pw")
    client.force_login(user)
    resp = client.get(reverse(link["url_name"]))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "<nav" in html
    assert link["title"] in html


def test_navigation_links_resolve():
    """Every defined navigation link should resolve to a valid URL."""
    links = navigation.get_navigation_links()
    assert len(links) == len(navigation.NAVIGATION_LINKS)
    for original, resolved in zip(navigation.NAVIGATION_LINKS, links):
        assert resolved["url"] == reverse(original["url_name"])


def test_get_navigation_links_raises_for_missing(monkeypatch):
    """The helper should raise if an invalid URL name is supplied."""
    bad_links = navigation.NAVIGATION_LINKS + [
        {"title": "Bad", "url_name": "does_not_exist"}
    ]
    monkeypatch.setattr(navigation, "NAVIGATION_LINKS", bad_links)
    with pytest.raises(NoReverseMatch):
        navigation.get_navigation_links()


@pytest.mark.django_db
def test_role_owner_sees_owner_money_navigation(django_user_model):
    owner_group, _ = Group.objects.get_or_create(name="Owner")
    user = django_user_model.objects.create_user(username="owner", password="pw")
    user.groups.add(owner_group)

    role = navigation.get_primary_role(user)
    groups = navigation.get_navigation_groups_for_role(role)
    visible_urls = {link["url_name"] for group in groups for link in group["links"]}

    assert role == navigation.ROLE_OWNER
    assert "root" in visible_urls
    assert "savings_ledger_list" in visible_urls
    assert "vendor_prices_list" in visible_urls
    assert "pos_sales_import" in visible_urls
    assert "variance_report" in visible_urls
    assert "indents_list" not in visible_urls


@pytest.mark.django_db
def test_role_purchase_sees_procurement_only_navigation(django_user_model):
    purchase_group, _ = Group.objects.get_or_create(name="Purchase")
    user = django_user_model.objects.create_user(username="purchase", password="pw")
    user.groups.add(purchase_group)

    role = navigation.get_primary_role(user)
    groups = navigation.get_navigation_groups_for_role(role)
    visible_urls = {link["url_name"] for group in groups for link in group["links"]}

    assert role == navigation.ROLE_PURCHASE
    assert "purchase_orders_list" in visible_urls
    assert "grn_list" in visible_urls
    assert "vendor_prices_list" in visible_urls
    assert "items_list" not in visible_urls
    assert "recipes_list" not in visible_urls


@pytest.mark.django_db
def test_role_kitchen_staff_sees_indent_requests_only(django_user_model):
    kitchen_group, _ = Group.objects.get_or_create(name="Kitchen Staff")
    user = django_user_model.objects.create_user(username="kitchen", password="pw")
    user.groups.add(kitchen_group)

    role = navigation.get_primary_role(user)
    groups = navigation.get_navigation_groups_for_role(role)
    visible_urls = {link["url_name"] for group in groups for link in group["links"]}

    assert role == navigation.ROLE_KITCHEN_STAFF
    assert visible_urls == {"indents_list"}


@pytest.mark.django_db
def test_role_head_chef_sees_sales_import(django_user_model):
    chef_group, _ = Group.objects.get_or_create(name="Head Chef")
    user = django_user_model.objects.create_user(username="chef", password="pw")
    user.groups.add(chef_group)

    role = navigation.get_primary_role(user)
    groups = navigation.get_navigation_groups_for_role(role)
    visible_urls = {link["url_name"] for group in groups for link in group["links"]}

    assert role == navigation.ROLE_HEAD_CHEF
    assert "pos_sales_import" in visible_urls
    assert "variance_report" in visible_urls


@pytest.mark.django_db
def test_primary_navigation_hx_request_still_returns_empty(django_user_model):
    user = django_user_model.objects.create_user(username="hx", password="pw")
    request = RequestFactory().get("/", HTTP_HX_REQUEST="true")
    request.user = user
    request.resolver_match = None

    ctx = navigation.primary_navigation(request)

    assert ctx["navigation_groups"] == []


@pytest.mark.django_db
def test_top_nav_uses_post_logout_form(django_user_model):
    user = django_user_model.objects.create_user(username="logout_u", password="pw")
    rf = RequestFactory()
    request = rf.get("/")
    request.user = user
    html = render_to_string("components/top_nav.html", request=request)

    assert f'action="{reverse("logout")}"' in html
    assert 'method="post"' in html
