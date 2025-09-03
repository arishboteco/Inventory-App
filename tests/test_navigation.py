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
    bad_links = navigation.NAVIGATION_LINKS + [{"title": "Bad", "url_name": "does_not_exist"}]
    monkeypatch.setattr(navigation, "NAVIGATION_LINKS", bad_links)
    with pytest.raises(NoReverseMatch):
        navigation.get_navigation_links()
