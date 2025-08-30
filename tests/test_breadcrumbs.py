import pytest
from django.urls import reverse
from django.utils import timezone
from inventory.models import PurchaseOrder


@pytest.mark.django_db
def test_purchase_order_detail_has_breadcrumbs(client, supplier_factory):
    supplier = supplier_factory()
    po = PurchaseOrder.objects.create(
        supplier=supplier,
        order_date=timezone.now().date(),
    )
    response = client.get(reverse("purchase_order_detail", args=[po.pk]))
    html = response.content.decode()
    assert f'href="{reverse("purchase_orders_list")}"' in html
    assert f"Purchase Order {po.pk}" in html
