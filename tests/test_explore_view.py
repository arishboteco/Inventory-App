import csv

import pytest
from django.urls import reverse

from inventory.models import Item

pytestmark = pytest.mark.django_db


def _create_item(name="Widget", active=True):
    return Item.objects.create(
        name=name,
        unit_id=55,
        reorder_point=1,
        notes="n",
        is_active=active,
    )


def test_explore_redirects_to_items(client):
    url = reverse("explore") + "?q=Banana&active=0"
    resp = client.get(url)
    assert resp.status_code == 301
    assert resp["Location"] == "/items/"


def test_explore_export_redirects_to_items(client):
    url = reverse("explore_export")
    resp = client.get(url)
    assert resp.status_code == 301
    assert resp["Location"] == "/items/"
