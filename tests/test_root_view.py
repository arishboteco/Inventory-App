import pytest


@pytest.mark.django_db
def test_root_view_shows_login_form_for_anonymous_user(client):
    client.logout()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b'name="username"' in resp.content


@pytest.mark.django_db
def test_login_route_redirects_to_root(client):
    client.logout()
    resp = client.get("/login/")
    assert resp.status_code == 302
    assert resp.url == "/"


@pytest.mark.django_db
def test_root_view_includes_kpis_for_authenticated_user(
    client, django_user_model, monkeypatch
):
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
    assert b'name="username"' not in resp.content


@pytest.mark.django_db
def test_root_view_includes_nav_counts_for_authenticated_user(
    client, django_user_model, monkeypatch
):
    user = django_user_model.objects.create_user(username="u", password="p")
    client.force_login(user)

    monkeypatch.setattr("inventory.services.kpis.stock_value", lambda: 0)
    monkeypatch.setattr("inventory.services.kpis.receipts_last_7_days", lambda: 0)
    monkeypatch.setattr("inventory.services.kpis.issues_last_7_days", lambda: 0)
    monkeypatch.setattr("inventory.services.kpis.low_stock_count", lambda: 0)

    monkeypatch.setattr("inventory.services.counts.item_count", lambda: 5)
    monkeypatch.setattr("inventory.services.counts.supplier_count", lambda: 7)
    monkeypatch.setattr("inventory.services.counts.pending_po_count", lambda: 2)

    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.context["item_count"] == 5
    assert resp.context["supplier_count"] == 7
    assert resp.context["pending_po_count"] == 2
    assert b"Items (5)" in resp.content
    assert b"Suppliers (7)" in resp.content
    assert b"Purchase Orders (2)" in resp.content
