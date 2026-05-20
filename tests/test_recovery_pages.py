from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from inventory.models import SavingsLedger, Supplier, VendorItemPrice

pytestmark = pytest.mark.django_db


def test_savings_ledger_page_lists_and_creates_entries(client, item_factory):
    item = item_factory(name="Ledger Chicken")
    SavingsLedger.objects.create(
        date=date.today(),
        item=item,
        saving_type=SavingsLedger.SavingType.VENDOR_SAVING,
        status=SavingsLedger.Status.CONFIRMED,
        confirmed_saving=Decimal("125.50"),
    )

    response = client.get(reverse("savings_ledger_list"))

    assert response.status_code == 200
    assert b"Savings Ledger" in response.content
    assert b"Ledger Chicken" in response.content
    assert b"125.50" in response.content

    post_response = client.post(
        reverse("savings_ledger_list"),
        {
            "date": date.today().isoformat(),
            "item": item.pk,
            "saving_type": SavingsLedger.SavingType.WASTE_REDUCTION,
            "source_document_type": "Manual",
            "source_document_id": "W-1",
            "baseline_price": "0",
            "selected_price": "0",
            "invoice_price": "0",
            "quantity": "2",
            "estimated_saving": "50.00",
            "confirmed_saving": "0",
            "lost_saving": "0",
            "status": SavingsLedger.Status.ESTIMATED,
            "notes": "Kitchen trial",
        },
    )

    assert post_response.status_code == 302
    assert SavingsLedger.objects.filter(
        saving_type=SavingsLedger.SavingType.WASTE_REDUCTION,
        estimated_saving=Decimal("50.00"),
    ).exists()


def test_vendor_prices_page_lists_and_creates_prices(client, item_factory):
    supplier = Supplier.objects.create(name="Recovery Vendor", is_active=True)
    item = item_factory(name="Vendor Paneer")
    VendorItemPrice.objects.create(
        vendor=supplier,
        item=item,
        unit=item.unit,
        price=Decimal("210.00"),
        effective_from=date.today(),
        source="Rate card",
    )

    response = client.get(reverse("vendor_prices_list"))

    assert response.status_code == 200
    assert b"Vendor Prices" in response.content
    assert b"Recovery Vendor" in response.content
    assert b"Vendor Paneer" in response.content

    post_response = client.post(
        reverse("vendor_prices_list"),
        {
            "vendor": supplier.pk,
            "item": item.pk,
            "unit": item.unit_id,
            "price": "205.00",
            "effective_from": date.today().isoformat(),
            "source": "Phone quote",
            "is_active": "on",
        },
    )

    assert post_response.status_code == 302
    assert VendorItemPrice.objects.filter(
        vendor=supplier,
        item=item,
        price=Decimal("205.00"),
        source="Phone quote",
        is_active=True,
    ).exists()
