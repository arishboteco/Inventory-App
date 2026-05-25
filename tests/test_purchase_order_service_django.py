from datetime import date
from decimal import Decimal

import pytest

from inventory.forms.purchase_forms import PurchaseOrderForm, PurchaseOrderItemFormSet
from inventory.models import (
    GoodsReceivedNote,
    GRNItem,
    PurchaseOrder,
    PurchaseOrderItem,
    SavingsLedger,
    Supplier,
    VendorItemPrice,
)
from inventory.services import purchase_order_service


@pytest.mark.django_db
def test_save_purchase_order_from_forms_creates(item_factory):
    supplier = Supplier.objects.create(name="Vendor", is_active=True)
    item = item_factory(name="Widget")
    form = PurchaseOrderForm(
        {
            "supplier": str(supplier.pk),
            "order_date": str(date.today()),
            "expected_delivery_date": "",
            "status": "DRAFT",
            "notes": "",
        }
    )
    formset = PurchaseOrderItemFormSet(
        {
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-item": str(item.pk),
            "items-0-quantity_ordered": "2",
            "items-0-unit_price": "3.00",
        },
        prefix="items",
    )
    assert form.is_valid(), form.errors
    assert formset.is_valid(), formset.errors
    po = purchase_order_service.save_purchase_order_from_forms(form, formset)
    assert po.pk
    assert po.supplier_id == supplier.pk
    assert po.purchaseorderitem_set.count() == 1


@pytest.mark.django_db
def test_save_purchase_order_from_forms_sets_expected_date_from_longest_item_lead_time(
    item_factory,
):
    supplier = Supplier.objects.create(name="Lead Time Vendor", is_active=True)
    short_lead = item_factory(name="Short Lead Item", lead_time_days=2)
    long_lead = item_factory(name="Long Lead Item", lead_time_days=7)
    order_date = date(2026, 5, 25)
    form = PurchaseOrderForm(
        {
            "supplier": str(supplier.pk),
            "order_date": str(order_date),
            "expected_delivery_date": "",
            "status": "DRAFT",
            "notes": "",
        }
    )
    formset = PurchaseOrderItemFormSet(
        {
            "items-TOTAL_FORMS": "2",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-item": str(short_lead.pk),
            "items-0-quantity_ordered": "2",
            "items-0-unit_price": "3.00",
            "items-1-item": str(long_lead.pk),
            "items-1-quantity_ordered": "1",
            "items-1-unit_price": "4.00",
        },
        prefix="items",
    )

    assert form.is_valid(), form.errors
    assert formset.is_valid(), formset.errors
    po = purchase_order_service.save_purchase_order_from_forms(form, formset)

    assert po.expected_delivery_date == date(2026, 6, 1)


@pytest.mark.django_db
def test_create_po_and_get_po(item_factory):
    supplier = Supplier.objects.create(name="Vendor")
    item = item_factory(name="Widget")
    po_id = purchase_order_service.create_po(
        {"supplier_id": supplier.pk, "order_date": date.today()},
        [{"item_id": item.item_id, "quantity_ordered": 5, "unit_price": 2.0}],
    )
    po = purchase_order_service.get_po_by_id(po_id)
    assert po["supplier_id"] == supplier.pk
    assert po["items"][0]["item_id"] == item.item_id


@pytest.mark.django_db
def test_get_orders_progress(item_factory):
    supplier = Supplier.objects.create(name="Vendor")
    item = item_factory(name="Widget")
    po = PurchaseOrder.objects.create(supplier=supplier, order_date=date.today())
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


@pytest.mark.django_db
def test_create_po_creates_estimated_vendor_savings(item_factory):
    supplier = Supplier.objects.create(name="Vendor")
    cheaper = Supplier.objects.create(name="Cheaper")
    item = item_factory(name="Rice", last_purchase_price="120.00")
    VendorItemPrice.objects.create(
        vendor=cheaper,
        item=item,
        price="100.00",
        effective_from=date.today(),
        is_active=True,
    )
    po_id = purchase_order_service.create_po(
        {"supplier_id": supplier.pk, "order_date": date.today()},
        [{"item_id": item.item_id, "quantity_ordered": 10, "unit_price": 110.0}],
    )
    entry = SavingsLedger.objects.get(
        source_document_type="PO",
        source_document_id=str(po_id),
        item=item,
    )
    assert entry.status == SavingsLedger.Status.ESTIMATED
    assert entry.estimated_saving == Decimal("0.00")
    assert entry.lost_saving == Decimal("100.00")
