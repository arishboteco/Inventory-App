import pytest
from django.db import connection

from inventory.models import Supplier
from inventory.services import supplier_service


@pytest.mark.django_db
def test_add_supplier_inserts_row():
    details = {"name": "Vendor A", "is_active": True}
    success, _ = supplier_service.add_supplier(details)
    assert success
    assert Supplier.objects.filter(name="Vendor A").exists()


@pytest.mark.django_db
def test_update_supplier_changes_fields():
    supplier = Supplier.objects.create(name="Vendor B", is_active=True)
    success, _ = supplier_service.update_supplier(supplier.pk, {"phone": "999"})
    assert success
    supplier.refresh_from_db()
    assert supplier.phone == "999"


@pytest.mark.django_db
def test_deactivate_and_reactivate_supplier():
    supplier = Supplier.objects.create(name="Vendor C", is_active=True)
    ok, _ = supplier_service.deactivate_supplier(supplier.pk)
    assert ok
    supplier.refresh_from_db()
    assert supplier.is_active is False
    ok, _ = supplier_service.reactivate_supplier(supplier.pk)
    assert ok
    supplier.refresh_from_db()
    assert supplier.is_active is True


@pytest.mark.django_db
def test_get_all_suppliers():
    Supplier.objects.create(name="Vendor 1", is_active=True)
    Supplier.objects.create(name="Vendor 2", is_active=True)
    Supplier.objects.create(name="Vendor 3", is_active=False)

    suppliers = supplier_service.get_all_suppliers()
    assert suppliers.count() == 2

    suppliers_all = supplier_service.get_all_suppliers(include_inactive=True)
    assert suppliers_all.count() == 3


@pytest.mark.django_db
def test_get_supplier_details():
    supplier = Supplier.objects.create(name="Vendor 1", contact_person="John Doe")
    details = supplier_service.get_supplier_details(supplier.pk)
    assert details is not None
    assert details["name"] == "Vendor 1"
    assert details["contact_person"] == "John Doe"
