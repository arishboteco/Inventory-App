import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_inline_update_updates_category_and_unit(client, item_factory):
    """Posting category/unit IDs should update the related FKs."""
    item = item_factory(unit_id=19, category_id=1)
    url = reverse("item_inline_update", args=[item.pk])

    resp = client.post(url, {"unit_id": "55", "category_id": "2"})

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "message": "Item updated"}

    item.refresh_from_db()
    assert item.unit_id == 55
    assert item.category_id == 2


def test_inline_update_ignores_invalid_fields(client, item_factory):
    """Fields not explicitly allowed should be ignored."""
    item = item_factory(name="Widget")
    url = reverse("item_inline_update", args=[item.pk])

    resp = client.post(url, {"base_unit": "pcs"})

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "message": "No changes"}

    item.refresh_from_db()
    assert item.name == "Widget"


def test_inline_update_updates_valid_field(client, item_factory):
    """Allowed scalar fields should be persisted."""
    item = item_factory(name="Widget")
    url = reverse("item_inline_update", args=[item.pk])

    resp = client.post(url, {"name": "Gizmo"})

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "message": "Item updated"}

    item.refresh_from_db()
    assert item.name == "Gizmo"
