
import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from inventory.models import Indent, Supplier


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
    """Ensure KPI cards display the expected counts."""
    item_factory(name="Foo", reorder_point=10, current_stock=5)
    Supplier.objects.create(name="Supp")
    Indent.objects.create(mrn="1", status="PENDING")

    resp = client.get(reverse("dashboard-kpis"))
    assert resp.status_code == 200
    assert b"Items" in resp.content
    assert b"Low-stock Items" in resp.content
    assert b"Suppliers" in resp.content
    assert b"Pending Indents" in resp.content
