from __future__ import annotations

import pytest
from django.core.management import call_command

from inventory.models import (
    ChefBulletin,
    POSMenuItemMapping,
    RecoveryAction,
    SaleTransaction,
    SavingsLedger,
    VendorItemPrice,
)

pytestmark = pytest.mark.django_db


def test_seed_dashboard_data_populates_phase10_surfaces():
    call_command("seed_dashboard_data", days=7)

    assert SaleTransaction.objects.exists()
    assert POSMenuItemMapping.objects.exists()
    assert VendorItemPrice.objects.exists()
    assert SavingsLedger.objects.exists()
    assert RecoveryAction.objects.exists()
    assert ChefBulletin.objects.exists()
