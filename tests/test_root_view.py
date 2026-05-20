import pytest


@pytest.mark.django_db
def test_root_view_shows_login_form_for_anonymous_user(client):
    client.logout()
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.url == "/accounts/login/"


@pytest.mark.django_db
def test_login_route_redirects_to_root(client):
    client.logout()
    resp = client.get("/login/")
    assert resp.status_code == 302
    assert resp.url == "/accounts/login/"


@pytest.mark.django_db
def test_root_view_includes_kpis_for_authenticated_user(client, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="p")
    client.force_login(user)

    resp = client.get("/")
    assert resp.status_code == 200
    assert "current_food_cost_pct" in resp.context
    assert "target_food_cost_pct" in resp.context
    assert "unrealised_profit" in resp.context
    assert "remaining_opportunity" in resp.context
    assert b'name="username"' not in resp.content


@pytest.mark.django_db
def test_root_view_provides_chart_data(client, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="p")
    client.force_login(user)

    resp = client.get("/")
    assert resp.status_code == 200
    assert "trend_labels" in resp.context
    assert "trend_consumption" in resp.context
    assert "trend_wastage" in resp.context
