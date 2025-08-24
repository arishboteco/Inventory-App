import csv
import pytest
from django.urls import reverse

from inventory.models import Item

pytestmark = pytest.mark.django_db


def _create_item(name="Widget", active=True):
    return Item.objects.create(
        name=name,
        base_unit="pcs",
        purchase_unit="box",
        permitted_departments="dept",
        reorder_point=1,
        notes="n",
        is_active=active,
    )


def test_explore_filters_by_query_and_active(client):
    _create_item("Apple", True)
    _create_item("Banana", False)
    url = reverse("explore") + "?q=Banana&active=0"
    resp = client.get(url)
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Banana" in content
    assert "Apple" not in content


def test_explore_export_csv(client):
    _create_item("Apple", True)
    url = reverse("explore_export")
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp["Content-Type"] == "text/csv"
    assert "attachment; filename=items.csv" in resp["Content-Disposition"]
    rows = list(csv.reader(resp.content.decode().splitlines()))
    assert rows[0] == ["ID", "Name", "Base Unit", "Current Stock", "Active"]
    assert rows[1][1] == "Apple"
