from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from inventory.models import (
    GoodsReceivedNote,
    GRNItem,
    Indent,
    PurchaseOrder,
    PurchaseOrderItem,
    StockTransaction,
    Supplier,
)
from inventory.models.enums import IndentStatus, PurchaseOrderStatus
from inventory.services import kpis


@pytest.mark.django_db
def test_low_stock_items_excludes_inactive(item_factory):
    item_factory(name="Active", reorder_point=10, current_stock=5)
    item_factory(name="Inactive", reorder_point=10, current_stock=5, is_active=False)
    assert kpis.low_stock_items() == ["Active"]


@pytest.mark.django_db
def test_kpi_calculations(item_factory):
    item1 = item_factory(name="A", reorder_point=20, current_stock=10)
    item2 = item_factory(name="B", reorder_point=1, current_stock=5)
    week_ago = timezone.now() - timedelta(days=2)
    StockTransaction.objects.create(
        item=item1,
        quantity_change=5,
        transaction_type="RECEIVING",
        transaction_date=week_ago,
    )
    StockTransaction.objects.create(
        item=item2,
        quantity_change=-2,
        transaction_type="ISSUE",
        transaction_date=week_ago,
    )

    assert kpis.stock_value() == 15
    assert kpis.receipts_last_7_days() == 5
    assert kpis.issues_last_7_days() == 2
    assert kpis.low_stock_count() == 1
    labels, values = kpis.stock_trend_last_7_days()
    assert labels and len(labels) == 7
    assert values[-1] == 3.0


@pytest.mark.django_db
def test_high_price_purchase_detection(item_factory, django_assert_num_queries):
    item = item_factory(name="X")
    supplier = Supplier.objects.create(name="Supp")
    po = PurchaseOrder.objects.create(
        supplier=supplier,
        order_date=timezone.now().date(),
        status=PurchaseOrderStatus.ORDERED,
    )
    poi = PurchaseOrderItem.objects.create(
        purchase_order=po, item=item, quantity_ordered=1, unit_price=Decimal("100")
    )
    grn1 = GoodsReceivedNote.objects.create(
        purchase_order=po, supplier=supplier, received_date=timezone.now().date()
    )
    GRNItem.objects.create(
        grn=grn1,
        po_item=poi,
        quantity_ordered_on_po=1,
        quantity_received=1,
        unit_price_at_receipt=Decimal("100"),
    )
    grn2 = GoodsReceivedNote.objects.create(
        purchase_order=po, supplier=supplier, received_date=timezone.now().date()
    )
    high = GRNItem.objects.create(
        grn=grn2,
        po_item=poi,
        quantity_ordered_on_po=1,
        quantity_received=1,
        unit_price_at_receipt=Decimal("150"),
    )
    grn3 = GoodsReceivedNote.objects.create(
        purchase_order=po, supplier=supplier, received_date=timezone.now().date()
    )
    GRNItem.objects.create(
        grn=grn3,
        po_item=poi,
        quantity_ordered_on_po=1,
        quantity_received=1,
        unit_price_at_receipt=Decimal("110"),
    )

    with django_assert_num_queries(1):
        flagged = kpis.high_price_purchases(Decimal("0.2"))
    assert flagged == [high]


@pytest.mark.django_db
def test_pending_po_and_indent_counts():
    supplier = Supplier.objects.create(name="S")
    PurchaseOrder.objects.create(
        supplier=supplier,
        order_date=timezone.now().date(),
        status=PurchaseOrderStatus.DRAFT,
    )
    PurchaseOrder.objects.create(
        supplier=supplier,
        order_date=timezone.now().date(),
        status=PurchaseOrderStatus.ORDERED,
    )
    PurchaseOrder.objects.create(
        supplier=supplier,
        order_date=timezone.now().date(),
        status=PurchaseOrderStatus.PARTIAL,
    )
    Indent.objects.create(mrn="1", status=IndentStatus.PENDING)
    Indent.objects.create(mrn="2", status=IndentStatus.SUBMITTED)
    Indent.objects.create(mrn="3", status=IndentStatus.PROCESSING)
    Indent.objects.create(mrn="4", status=IndentStatus.COMPLETED)

    po_counts = kpis.pending_po_status_counts()
    indent_counts = kpis.pending_indent_counts()

    assert po_counts == {
        PurchaseOrderStatus.DRAFT: 1,
        PurchaseOrderStatus.ORDERED: 1,
        PurchaseOrderStatus.PARTIAL: 1,
    }
    assert indent_counts == {
        IndentStatus.PENDING: 1,
        IndentStatus.SUBMITTED: 1,
        IndentStatus.PROCESSING: 1,
    }


@pytest.mark.django_db
def test_stale_items(item_factory):
    fresh = item_factory(name="Fresh")
    stale = item_factory(name="Old")
    item_factory(name="Never")

    now = timezone.now()
    StockTransaction.objects.create(
        item=fresh,
        quantity_change=1,
        transaction_type="RECEIVING",
        transaction_date=now,
    )
    old_date = now - timedelta(days=40)
    old_tx = StockTransaction.objects.create(
        item=stale,
        quantity_change=1,
        transaction_type="RECEIVING",
    )
    old_tx.transaction_date = old_date
    old_tx.save(update_fields=["transaction_date"])

    result = kpis.stale_items(days=30)
    assert result == ["Never", "Old"]
