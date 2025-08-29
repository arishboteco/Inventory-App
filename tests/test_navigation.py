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
        "Items",
        "Orders",
        "Indents",
        "Receiving",
        "Reports",
    ]
    for text in expected:
        assert text in html


@pytest.mark.django_db
def test_home_page_contains_nav_links(client, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="pw")
    client.force_login(user)
    resp = client.get(reverse("root"))
    html = resp.content.decode()
    expected = [
        "Dashboard",
        "Items",
        "Orders",
        "Indents",
        "Receiving",
        "Reports",
    ]
    for text in expected:
        assert text in html
