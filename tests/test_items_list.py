from datetime import date
from decimal import Decimal

from django.urls import reverse

from inventory.models import (
    Item,
    PurchaseOrder,
    PurchaseOrderItem,
    StockTransaction,
    Supplier,
)


def _create_item(**kwargs):
    defaults = {
        "name": "Widget",
        "unit_id": 55,
        "reorder_point": 1,
        "notes": "n",
        "is_active": True,
        "category_id": 1,
    }
    defaults.update(kwargs)
    return Item.objects.create(**defaults)


def test_item_link_in_grid_layout(client):
    item = _create_item()
    resp = client.get(reverse("items_table") + "?layout=grid")
    assert resp.status_code == 200
    assert reverse("item_detail", args=[item.pk]) in resp.content.decode()


def test_item_link_in_table_layout(client):
    item = _create_item()
    resp = client.get(reverse("items_table") + "?layout=table")
    assert resp.status_code == 200
    assert reverse("item_detail", args=[item.pk]) in resp.content.decode()


def test_archive_action_toggles_item(client):
    item = _create_item()
    resp = client.get(reverse("items_table") + "?layout=grid")
    assert "data-action=\"archive\"" in resp.content.decode()

    url = reverse("item_toggle_active", args=[item.pk])
    client.post(url, {"page": "1"})
    item.refresh_from_db()
    assert item.is_active is False

    client.post(url, {"page": "1"})
    item.refresh_from_db()
    assert item.is_active is True


def test_item_detail_includes_supplier_and_movements(client):
    item = _create_item()
    supplier = Supplier.objects.create(name="Acme Corp")
    po = PurchaseOrder.objects.create(supplier=supplier, order_date=date.today())
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        item=item,
        quantity_ordered=1,
        unit_price=Decimal("1.00"),
    )
    tx = StockTransaction.objects.create(
        item=item, quantity_change=Decimal("5"), transaction_type="IN"
    )
    resp = client.get(reverse("item_detail", args=[item.pk]))
    content = resp.content.decode()
    assert supplier.name in content
    assert tx.transaction_type in content
    assert str(tx.quantity_change) in content
