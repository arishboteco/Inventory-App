"""
Post-submit / CRUD smoke tests for high-risk flows (native POST vs drawer JSON).

See docs/CRUD_POST_SUBMIT_AUDIT.md for the full matrix.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from inventory.models import PurchaseOrder, PurchaseOrderItem, Supplier

pytestmark = pytest.mark.django_db


def test_stock_receive_native_post_redirects_to_full_stock_movements(
    client, item_factory
):
    """Receive Stock modal uses native POST; success must redirect to full list (not a partial)."""
    item = item_factory(name="AuditReceiveItem", current_stock=Decimal("0"))
    url = reverse("stock_movements")
    data = {
        "submit_receive": "1",
        "receive-item": str(item.pk),
        "receive-quantity_change": "2.5",
        "receive-related_po": "",
    }
    resp = client.post(url, data)
    assert resp.status_code == 302
    assert resp["Location"] == reverse("stock_movements")

    final = client.get(reverse("stock_movements"))
    assert final.status_code == 200
    body = final.content.decode()
    assert "Stock Movements" in body or "Transactions" in body


def test_po_receive_partial_xhr_returns_json_with_redirect(client, item_factory):
    """Drawer receive must return JSON with redirect (modal.js), not a full-page dead end."""
    supplier = Supplier.objects.create(name="AuditPOVendor")
    item = item_factory(name="POLineItem")
    po = PurchaseOrder.objects.create(
        supplier=supplier, order_date=date.today(), status="SENT"
    )
    poi = PurchaseOrderItem.objects.create(
        purchase_order=po,
        item=item,
        quantity_ordered=Decimal("10"),
        unit_price=Decimal("1.00"),
    )

    url = reverse("purchase_order_receive_partial", args=[po.pk])
    data = {
        "partial": "1",
        "received_date": date.today().isoformat(),
        "notes": "",
        f"item_{poi.pk}": "2",
    }
    resp = client.post(
        url,
        data,
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        HTTP_ACCEPT="application/json",
    )
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("application/json")
    payload = resp.json()
    assert payload.get("ok") is True
    assert "redirect" in payload
    assert str(po.pk) in payload["redirect"]


def test_item_inline_stock_update_returns_json(client, item_factory):
    """Items table restock path: inline current_stock via JSON (no navigation)."""
    item = item_factory(name="InlineStock", current_stock=Decimal("1"))
    url = reverse("item_inline_update", args=[item.pk])
    resp = client.post(url, {"current_stock": "7.25"})
    assert resp.status_code == 200
    assert resp.json().get("ok") is True
    item.refresh_from_db()
    assert item.current_stock == Decimal("7.25")
