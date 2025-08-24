from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from inventory.models import Indent, PurchaseOrder, StockTransaction, Supplier


@pytest.mark.django_db
def test_dashboard_low_stock(client, item_factory):
    item_factory(name="Foo", reorder_point=10, current_stock=5)
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200
    assert b"Foo" in resp.content


@pytest.mark.django_db
def test_dashboard_kpis_endpoint(client, item_factory):
    fresh = item_factory(name="Foo", reorder_point=10, current_stock=5)
    StockTransaction.objects.create(
        item=fresh,
        quantity_change=1,
        transaction_type="RECEIVING",
        transaction_date=timezone.now(),
    )
    stale = item_factory(name="Old")
    old_tx = StockTransaction.objects.create(
        item=stale,
        quantity_change=1,
        transaction_type="RECEIVING",
    )
    old_tx.transaction_date = timezone.now() - timedelta(days=40)
    old_tx.save(update_fields=["transaction_date"])
    supplier = Supplier.objects.create(name="Supp")
    PurchaseOrder.objects.create(
        supplier=supplier, order_date=timezone.now().date(), status="DRAFT"
    )
    Indent.objects.create(mrn="1", status="PENDING")

    resp = client.get(reverse("dashboard-kpis"))
    assert resp.status_code == 200
    assert b"Low-stock Items" in resp.content
    assert b"Stale Items" in resp.content
    assert b"Old" in resp.content
    assert b"High-price Purchases" in resp.content
    assert b"Pending POs" in resp.content
    assert b"Pending Indents" in resp.content
