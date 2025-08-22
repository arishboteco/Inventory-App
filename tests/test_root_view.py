import pytest
from django.urls import reverse
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_root_view_redirects_when_authenticated(client):
    User.objects.create_user(username="u", password="p")
    client.login(username="u", password="p")
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.url == reverse("dashboard")


@pytest.mark.django_db
def test_root_view_renders_home_for_anonymous(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Django is running" in resp.content
