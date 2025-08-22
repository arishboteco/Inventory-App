import pytest
from django.urls import reverse

from inventory.models import Item


@pytest.mark.django_db
def test_dashboard_low_stock(client):
    Item.objects.create(name="Foo", reorder_point=10, current_stock=5)
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200
    assert b"Foo" in resp.content
