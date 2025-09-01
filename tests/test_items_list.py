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

import pytest


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
    edit_url = reverse("item_edit", args=[item.pk])
    html = resp.content.decode()
    assert f'href="{edit_url}"' in html
    assert f'data-modal-url="{edit_url}?partial=1"' in html


def test_item_link_in_table_layout(client):
    item = _create_item()
    resp = client.get(reverse("items_table") + "?layout=table")
    assert resp.status_code == 200
    assert reverse("item_detail", args=[item.pk]) in resp.content.decode()


def test_archive_action_toggles_item(client):
    item = _create_item()
    detail_url = reverse("item_detail", args=[item.pk])
    resp = client.get(detail_url)

    toggle_url = reverse("item_toggle_active", args=[item.pk])
    html = resp.content.decode()
    assert f'action="{toggle_url}"' in html
    assert 'method="post"' in html

    client.post(toggle_url)
    item.refresh_from_db()
    assert item.is_active is False

    client.post(toggle_url)
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
    assert '<h2 class="text-lg font-semibold">Supplier History</h2>' in content
    assert '<h2 class="text-lg font-semibold">Stock Movements</h2>' in content


@pytest.mark.django_db
def test_items_list_kpi_card_links(client):
    _create_item()
    url = reverse("items_list")
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.content.decode()
    po_url = reverse("purchase_orders_list")
    assert html.count(f'href="{url}"') >= 2
    assert f'href="{url}?stock_status=low"' in html
    assert f'href="{po_url}?status=ORDERED"' in html
