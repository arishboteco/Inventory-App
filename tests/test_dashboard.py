import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from inventory.models import Indent, StockTransaction, Supplier

@pytest.mark.django_db
def test_dashboard_low_stock(client, item_factory, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="pw")
    perm = Permission.objects.get(codename="add_purchaseorder")
    user.user_permissions.add(perm)
    client.force_login(user)
    item_factory(name="Foo", reorder_point=10, current_stock=5)
    item_factory(name="Inactive", reorder_point=10, current_stock=5, is_active=False)
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200
    assert b"Foo" in resp.content
    assert b"Inactive" not in resp.content


@pytest.mark.django_db
def test_dashboard_kpis_endpoint(client, item_factory):
    fresh = item_factory(name="Foo", reorder_point=10, current_stock=5)
    StockTransaction.objects.create(
        item=fresh,
        quantity_change=1,
        transaction_type="RECEIVING",
        transaction_date=timezone.now(),
    )

    Supplier.objects.create(name="Supp")
    Indent.objects.create(mrn="1", status="PENDING")

    resp = client.get(reverse("dashboard-kpis"))
    assert resp.status_code == 200
    assert b"Items" in resp.content
    assert b"Low-stock Items" in resp.content
    assert b"Suppliers" in resp.content
    assert b"Pending Indents" in resp.content
