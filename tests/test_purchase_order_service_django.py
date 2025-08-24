import pytest
from datetime import date

from inventory.models import (
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem,
    GoodsReceivedNote,
    GRNItem,
)
from inventory.services import purchase_order_service


@pytest.mark.django_db
def test_create_po_and_get_po(item_factory):
    supplier = Supplier.objects.create(name="Vendor")
    item = item_factory(name="Widget")
    success, msg, po_id = purchase_order_service.create_po(
        {"supplier_id": supplier.pk, "order_date": date.today()},
        [{"item_id": item.item_id, "quantity_ordered": 5, "unit_price": 2.0}],
    )
    assert success, msg
    po = purchase_order_service.get_po_by_id(po_id)
    assert po["supplier_id"] == supplier.pk
    assert po["items"][0]["item_id"] == item.item_id


@pytest.mark.django_db
def test_get_orders_progress(item_factory):
    supplier = Supplier.objects.create(name="Vendor")
    item = item_factory(name="Widget")
    po = PurchaseOrder.objects.create(
        supplier=supplier, order_date=date.today()
    )
    poi = PurchaseOrderItem.objects.create(
        purchase_order=po,
        item=item,
        quantity_ordered=10,
        unit_price=1,
    )
    grn = GoodsReceivedNote.objects.create(
        purchase_order=po,
        supplier=supplier,
        received_date=date.today(),
    )
    GRNItem.objects.create(
        grn=grn,
        po_item=poi,
        quantity_ordered_on_po=10,
        quantity_received=4,
        unit_price_at_receipt=1,
    )
    progress = purchase_order_service.get_orders_progress([po.pk])
    assert progress[po.pk]["ordered_total"] == 10
    assert progress[po.pk]["received_total"] == 4
    assert progress[po.pk]["percent"] == 40
