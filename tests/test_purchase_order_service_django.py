import pytest
from datetime import date
from django.db import connection

from inventory.models import Supplier, Item, PurchaseOrder, PurchaseOrderItem
from inventory.services import purchase_order_service


@pytest.mark.django_db
def test_create_po_and_get_po():
    supplier = Supplier.objects.create(name="Vendor")
    item = Item.objects.create(name="Widget")
    success, msg, po_id = purchase_order_service.create_po(
        {"supplier_id": supplier.pk, "order_date": date.today()},
        [{"item_id": item.item_id, "quantity_ordered": 5, "unit_price": 2.0}],
    )
    assert success, msg
    po = purchase_order_service.get_po_by_id(po_id)
    assert po["supplier_id"] == supplier.pk
    assert po["items"][0]["item_id"] == item.item_id
