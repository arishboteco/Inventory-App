import pytest
from django.urls import reverse
from django.contrib.auth.models import User

from inventory.models import Item


@pytest.mark.django_db
def test_dashboard_low_stock(client):
    User.objects.create_user(username="u", password="p")
    Item.objects.create(name="Foo", reorder_point=10, current_stock=5)
    client.login(username="u", password="p")
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200
    assert b"Foo" in resp.content
