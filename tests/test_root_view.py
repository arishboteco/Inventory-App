import pytest


@pytest.mark.django_db
def test_root_view_renders_home(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Django is running" in resp.content
