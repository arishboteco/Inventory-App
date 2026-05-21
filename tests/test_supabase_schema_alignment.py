from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.urls import reverse

from inventory.models import (
    GoodsReceivedNote,
    Indent,
    IndentItem,
    PurchaseOrder,
    SaleTransaction,
    Supplier,
)
from inventory.serializers import (
    GoodsReceivedNoteSerializer,
    ItemSerializer,
    PurchaseOrderSerializer,
    SupplierSerializer,
)


@pytest.mark.django_db
def test_adhoc_grn_creation_persists_grn_number(client, item_factory):
    supplier = Supplier.objects.create(name="Adhoc Vendor")
    item = item_factory(name="Adhoc Tomato", current_stock=Decimal("0"))

    response = client.post(
        reverse("grn_create_adhoc"),
        {
            "supplier": supplier.pk,
            "received_date": date.today().isoformat(),
            "delivery_note_number": "INV-001",
            "notes": "Direct receipt",
            "lines-TOTAL_FORMS": "3",
            "lines-INITIAL_FORMS": "0",
            "lines-MIN_NUM_FORMS": "1",
            "lines-MAX_NUM_FORMS": "1000",
            "lines-0-item": item.pk,
            "lines-0-quantity_received": "2.00",
            "lines-0-unit_price": "30.00",
            "lines-0-item_notes": "",
            "lines-1-item": "",
            "lines-1-quantity_received": "",
            "lines-1-unit_price": "",
            "lines-1-item_notes": "",
            "lines-2-item": "",
            "lines-2-quantity_received": "",
            "lines-2-unit_price": "",
            "lines-2-item_notes": "",
        },
    )

    assert response.status_code == 302
    grn = GoodsReceivedNote.objects.get(supplier=supplier)
    assert grn.grn_number == "GRN-0001"
    assert grn.delivery_note_number == "INV-001"


@pytest.mark.django_db
def test_sales_transactions_table_exists_and_model_writes():
    assert SaleTransaction._meta.db_table in connection.introspection.table_names()
    sale = SaleTransaction.objects.create(quantity=Decimal("3.00"), notes="Walk-in")
    assert sale.sale_id


@pytest.mark.django_db
def test_api_serializers_expose_stored_planning_and_document_fields(item_factory):
    supplier = Supplier.objects.create(
        name="API Vendor",
        tax_id="GST123",
        payment_terms="Net 30",
        credit_limit=Decimal("5000.00"),
        supplier_rating=4,
    )
    item = item_factory(
        name="API Rice",
        initial_purchase_price=Decimal("40.00"),
        last_purchase_price=Decimal("44.00"),
        preferred_supplier=supplier,
        minimum_order_qty=Decimal("5.00"),
        lead_time_days=2,
    )
    po = PurchaseOrder.objects.create(supplier=supplier, order_date=date.today())
    grn = GoodsReceivedNote.objects.create(
        supplier=supplier,
        purchase_order=po,
        received_date=date.today(),
        delivery_note_number="DN-7",
    )

    item_data = ItemSerializer(item).data
    supplier_data = SupplierSerializer(supplier).data
    po_data = PurchaseOrderSerializer(po).data
    grn_data = GoodsReceivedNoteSerializer(grn).data

    assert item_data["initial_purchase_price"] == "40.00"
    assert item_data["last_purchase_price"] == "44.00"
    assert item_data["preferred_supplier"] == supplier.pk
    assert item_data["minimum_order_qty"] == "5.00"
    assert item_data["lead_time_days"] == 2
    assert supplier_data["tax_id"] == "GST123"
    assert supplier_data["payment_terms"] == "Net 30"
    assert supplier_data["credit_limit"] == "5000.00"
    assert supplier_data["supplier_rating"] == 4
    assert po_data["po_number"] == po.po_number
    assert grn_data["grn_number"] == grn.grn_number
    assert grn_data["delivery_note_number"] == "DN-7"
    assert "attachment" in grn_data


@pytest.mark.django_db
def test_model_status_defaults_are_uppercase_enum_values(item_factory):
    supplier = Supplier.objects.create(name="Default Vendor")
    item = item_factory(name="Default Flour")
    indent = Indent.objects.create(mrn="MRN-DEFAULT")
    indent_item = IndentItem.objects.create(indent=indent, item=item)
    po = PurchaseOrder.objects.create(supplier=supplier, order_date=date.today())

    assert indent.status == "SUBMITTED"
    assert indent_item.item_status == "PENDING"
    assert po.status == "DRAFT"
