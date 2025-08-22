import pytest
from django.urls import reverse
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_root_view_renders_home_for_anonymous(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Django is running" in resp.content
