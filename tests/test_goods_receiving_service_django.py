from datetime import date

import pytest

from inventory.models import PurchaseOrder, PurchaseOrderItem, Supplier
from inventory.services import goods_receiving_service, purchase_order_service


@pytest.mark.django_db
def test_create_grn_updates_stock_and_po(item_factory):
    supplier = Supplier.objects.create(name="Vendor")
    item = item_factory(name="Widget", current_stock=0)
    success, msg, po_id = purchase_order_service.create_po(
        {"supplier_id": supplier.pk, "order_date": date.today()},
        [{"item_id": item.item_id, "quantity_ordered": 10, "unit_price": 1.0}],
    )
    assert success, msg
    po_item = PurchaseOrderItem.objects.get(
        purchase_order_id=po_id, item_id=item.item_id
    )
    grn_data = {
        "po_id": po_id,
        "supplier_id": supplier.pk,
        "received_date": date.today(),
        "received_by_user_id": "tester",
    }
    items_data = [
        {
            "item_id": item.item_id,
            "po_item_id": po_item.pk,
            "quantity_ordered_on_po": po_item.quantity_ordered,
            "quantity_received": 5,
            "unit_price_at_receipt": po_item.unit_price,
        }
    ]
    success, msg, grn_id = goods_receiving_service.create_grn(grn_data, items_data)
    assert success, msg
    item.refresh_from_db()
    assert item.current_stock == 5
    po_item.refresh_from_db()
    assert po_item.received_total == 5
    po = PurchaseOrder.objects.get(pk=po_id)
    assert po.status == "PARTIAL"
