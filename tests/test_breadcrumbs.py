import pytest
from django.template.loader import render_to_string
from django.urls import reverse


@pytest.mark.django_db
def test_breadcrumb_component_includes_root(django_user_model):
    html = render_to_string(
        "components/breadcrumb.html",
        {
            "list_url": reverse("items_list"),
            "list_title": "Inventory",
            "current_title": "Item 1",
        },
    )
    assert f'href="{reverse("root")}"' in html
    assert "Inventory Pro" in html
    assert "Inventory" in html
    assert "Item 1" in html


@pytest.mark.django_db
def test_dashboard_page_displays_breadcrumb(client, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="pw")
    client.force_login(user)
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Inventory Pro" in html
    assert "Dashboard" in html
    assert "flex items-center gap-1 text-sm text-gray-500 mb-4" in html
