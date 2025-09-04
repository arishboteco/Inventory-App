import json
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
def test_root_view_includes_kpis_for_authenticated_user(client, django_user_model, monkeypatch):
    user = django_user_model.objects.create_user(username="u", password="p")
    client.force_login(user)

    monkeypatch.setattr("inventory.services.counts.item_count", lambda: 5)
    monkeypatch.setattr("inventory.services.kpis.low_stock_count", lambda: 4)
    monkeypatch.setattr("inventory.services.counts.supplier_count", lambda: 7)
    monkeypatch.setattr(
        "inventory.services.kpis.pending_indent_counts", lambda: {"p": 2}
    )

    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.context["item_count"] == 5
    assert resp.context["low_stock"] == 4
    assert resp.context["supplier_count"] == 7
    assert resp.context["pending_indents"] == 2
    assert b'name="username"' not in resp.content


@pytest.mark.django_db
def test_root_view_provides_chart_data(client, django_user_model, monkeypatch):
    user = django_user_model.objects.create_user(username="u", password="p")
    client.force_login(user)

    monkeypatch.setattr(
        "core.views._stock_trend_data", lambda **_: (["2024-01-01"], [1.0])
    )

    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.context["trend_labels"] == json.dumps(["2024-01-01"])
    assert resp.context["trend_values"] == json.dumps([1.0])
