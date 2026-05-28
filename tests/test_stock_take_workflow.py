from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from inventory.models import StockTake, StockTakeItem, StockTransaction

pytestmark = pytest.mark.django_db


def test_completed_stock_take_cannot_be_discarded(client, django_user_model, item_factory):
    user = django_user_model.objects.get(username="admin")
    item = item_factory(name="Completed Stock Take Item", current_stock=Decimal("8.00"))
    stock_take = StockTake.objects.create(
        date=date.today(),
        status="COMPLETED",
        created_by=user,
    )
    StockTakeItem.objects.create(
        stock_take=stock_take,
        item=item,
        system_qty=Decimal("8.000"),
        physical_qty=Decimal("7.000"),
    )
    StockTransaction.objects.create(
        item=item,
        quantity_change=Decimal("-1.00"),
        transaction_type="ADJUSTMENT",
        notes=f"Stock take #{stock_take.pk} variance adjustment",
    )

    response = client.post(
        reverse("stock_take_review", args=[stock_take.pk]),
        {"action": "discard"},
    )

    assert response.status_code == 302
    assert StockTake.objects.filter(pk=stock_take.pk).exists()
    assert StockTransaction.objects.filter(item=item).count() == 1
