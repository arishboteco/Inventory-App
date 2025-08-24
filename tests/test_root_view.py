import pytest


@pytest.mark.django_db
def test_root_view_shows_login_form_for_anonymous_user(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"name=\"username\"" in resp.content


@pytest.mark.django_db
def test_login_route_redirects_to_root(client):
    resp = client.get("/login/")
    assert resp.status_code == 302
    assert resp.url == "/"


@pytest.mark.django_db
def test_root_view_includes_kpis_for_authenticated_user(client, django_user_model, monkeypatch):
    user = django_user_model.objects.create_user(username="u", password="p")
    client.force_login(user)

    monkeypatch.setattr("inventory.services.kpis.stock_value", lambda: 10)
    monkeypatch.setattr("inventory.services.kpis.receipts_last_7_days", lambda: 2)
    monkeypatch.setattr("inventory.services.kpis.issues_last_7_days", lambda: 3)
    monkeypatch.setattr("inventory.services.kpis.low_stock_count", lambda: 4)

    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.context["stock_value"] == 10
    assert resp.context["receipts"] == 2
    assert resp.context["issues"] == 3
    assert resp.context["low_stock"] == 4
    assert b"name=\"username\"" not in resp.content
