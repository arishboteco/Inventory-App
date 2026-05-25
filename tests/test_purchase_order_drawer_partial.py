"""Purchase order drawer partial: structure and JSON validation errors."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from inventory.models import (
    GoodsReceivedNote,
    GRNItem,
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def po_staff_client(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="po_drawer_tester",
        password="testpass123",
        is_staff=True,
    )
    client.force_login(user)
    return client


def test_purchase_order_create_partial_get_has_drawer_hooks(po_staff_client):
    url = reverse("purchase_order_create_partial")
    resp = po_staff_client.get(url)
    assert resp.status_code == 200
    content = resp.content.decode()
    assert 'id="po-drawer-form"' in content
    assert 'id="po-item-prices"' in content
    assert 'type="application/json"' in content
    assert 'id="items-formset"' in content
    assert "supplier-options" in content
    assert "hx-get" in content
    assert "drawer-panel max-w-drawer-xl flex flex-col min-h-0" in content
    assert "p-4 flex-1 min-h-0 overflow-y-auto" in content

    soup = BeautifulSoup(content, "html.parser")
    notes = soup.find("textarea", attrs={"name": "notes"})
    assert notes is not None
    grid = soup.find(
        "div",
        class_=lambda value: value and "grid-cols-2" in value and "gap-4" in value,
    )
    assert grid is not None
    assert grid.find("textarea", attrs={"name": "notes"}) is None


def test_purchase_order_create_partial_post_validation_returns_json(po_staff_client):
    """Invalid partial POST must return JSON (modal.js), not HTML."""
    supplier = Supplier.objects.create(name="Drawer Supplier JSON")
    url = reverse("purchase_order_create_partial")
    resp = po_staff_client.post(
        url,
        {
            "partial": "1",
            "csrfmiddlewaretoken": po_staff_client.session.get(
                "_csrftoken", "test-csrf"
            ),
            "supplier": str(supplier.pk),
            "order_date": "",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-item": "",
            "items-0-quantity_ordered": "",
            "items-0-unit_price": "",
        },
    )
    assert resp.status_code == 400
    assert resp["Content-Type"].startswith("application/json")
    payload = json.loads(resp.content)
    assert payload.get("ok") is False
    assert "message" in payload
    assert "errors" in payload


def test_purchase_order_edit_partial_post_validation_returns_json(
    po_staff_client, item_factory
):
    supplier = Supplier.objects.create(name="Edit Drawer Supplier")
    item = item_factory(name="Line Item X")
    po = PurchaseOrder.objects.create(
        supplier=supplier,
        order_date=date.today(),
        status="DRAFT",
    )
    url = reverse("purchase_order_edit_partial", kwargs={"pk": po.pk})
    resp = po_staff_client.post(
        url,
        {
            "partial": "1",
            "csrfmiddlewaretoken": po_staff_client.session.get(
                "_csrftoken", "test-csrf"
            ),
            "supplier": str(supplier.pk),
            "order_date": "",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-item": str(item.pk),
            "items-0-quantity_ordered": "0",
            "items-0-unit_price": "1.00",
        },
    )
    assert resp.status_code == 400
    data = json.loads(resp.content)
    assert data.get("ok") is False
    assert "errors" in data


def test_purchase_order_full_form_notes_not_inside_two_column_grid(po_staff_client):
    resp = po_staff_client.get(reverse("purchase_order_create"))
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content.decode(), "html.parser")

    notes = soup.find("textarea", attrs={"name": "notes"})
    assert notes is not None

    grid = soup.find(
        "div",
        class_=lambda value: value and "grid-cols-2" in value and "gap-4" in value,
    )
    assert grid is not None
    assert grid.find("textarea", attrs={"name": "notes"}) is None


def test_purchase_order_detail_actions_use_drawers(po_staff_client, item_factory):
    supplier = Supplier.objects.create(name="Detail Drawer Supplier")
    item = item_factory(name="Detail Drawer Item")
    po = PurchaseOrder.objects.create(
        supplier=supplier,
        order_date=date.today(),
        status="SENT",
    )
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        item=item,
        quantity_ordered=Decimal("3.00"),
        unit_price=Decimal("4.00"),
    )

    resp = po_staff_client.get(reverse("purchase_order_detail", args=[po.pk]))
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content.decode(), "html.parser")

    receive = soup.find(
        "a",
        attrs={
            "data-modal-url": reverse("purchase_order_receive_partial", args=[po.pk])
        },
    )
    edit = soup.find(
        "a",
        attrs={"data-modal-url": reverse("purchase_order_edit_partial", args=[po.pk])},
    )
    assert receive is not None
    assert receive.get("data-modal-type") == "drawer"
    assert edit is not None
    assert edit.get("data-modal-type") == "drawer"


def test_purchase_order_receive_partial_rejects_draft_json(
    po_staff_client, item_factory
):
    supplier = Supplier.objects.create(name="Draft Receive Supplier")
    item = item_factory(name="Draft Receive Item")
    po = PurchaseOrder.objects.create(
        supplier=supplier,
        order_date=date.today(),
        status="DRAFT",
    )
    poi = PurchaseOrderItem.objects.create(
        purchase_order=po,
        item=item,
        quantity_ordered=Decimal("3.00"),
        unit_price=Decimal("4.00"),
    )

    resp = po_staff_client.post(
        reverse("purchase_order_receive_partial", args=[po.pk]),
        {
            "partial": "1",
            "received_date": date.today().isoformat(),
            f"item_{poi.pk}": "1",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        HTTP_ACCEPT="application/json",
    )

    assert resp.status_code == 400
    data = resp.json()
    assert data["ok"] is False
    assert "Only sent purchase orders can receive goods" in data["message"]


def test_purchase_order_edit_partial_rejects_deleting_received_line(
    po_staff_client, item_factory
):
    supplier = Supplier.objects.create(name="Received Line Supplier")
    item = item_factory(name="Received Line Item")
    po = PurchaseOrder.objects.create(
        supplier=supplier,
        order_date=date.today(),
        status="SENT",
    )
    poi = PurchaseOrderItem.objects.create(
        purchase_order=po,
        item=item,
        quantity_ordered=Decimal("3.00"),
        unit_price=Decimal("4.00"),
    )
    grn = GoodsReceivedNote.objects.create(
        purchase_order=po,
        supplier=supplier,
        received_date=date.today(),
    )
    GRNItem.objects.create(
        grn=grn,
        po_item=poi,
        item=item,
        quantity_ordered_on_po="3.00",
        quantity_received="1.00",
        unit_price_at_receipt="4.00",
    )

    resp = po_staff_client.post(
        reverse("purchase_order_edit_partial", args=[po.pk]),
        {
            "partial": "1",
            "supplier": str(supplier.pk),
            "order_date": date.today().isoformat(),
            "expected_delivery_date": "",
            "status": "SENT",
            "notes": "",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "1",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-po_item_id": str(poi.pk),
            "items-0-item": str(item.pk),
            "items-0-quantity_ordered": "3.00",
            "items-0-unit_price": "4.00",
            "items-0-DELETE": "on",
        },
    )

    assert resp.status_code == 400
    assert "Cannot delete" in resp.json()["message"]
