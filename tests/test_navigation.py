import pytest
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse


@pytest.mark.django_db
def test_nav_template_contains_links():
    rf = RequestFactory()
    request = rf.get("/")
    request.user = AnonymousUser()
    html = render_to_string("components/nav.html", {"request": request})
    expected = [
        "Overview",
        "Inventory",
        "Procurement",
        "Production",
        "Account",
        "Dashboard",
        "Reports",
        "Items",
        "Stock Movements",
        "Suppliers",
        "Indents",
        "Purchase Orders",
        "GRNs",
        "Recipes",
        "Login",
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
        "Overview",
        "Inventory",
        "Procurement",
        "Production",
        "Account",
        "Dashboard",
        "Reports",
        "Items",
        "Stock Movements",
        "Suppliers",
        "Indents",
        "Purchase Orders",
        "GRNs",
        "Recipes",
        "Logout",
    ]
    for text in expected:
        assert text in html
