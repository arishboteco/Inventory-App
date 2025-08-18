import pytest
from inventory.models import Supplier
from inventory.services import supplier_service


@pytest.mark.django_db
def test_add_supplier_inserts_row():
    details = {
        "name": "Vendor A",
        "contact_person": "John",
        "phone": "123",
        "email": "john@example.com",
        "address": "Addr",
        "notes": "Note",
        "is_active": True,
    }
    success, _ = supplier_service.add_supplier(details)
    assert success
    assert Supplier.objects.filter(name="Vendor A").exists()


@pytest.mark.django_db
def test_add_supplier_duplicate_name_fails():
    details = {"name": "Dup", "is_active": True}
    supplier_service.add_supplier(details)
    success, _ = supplier_service.add_supplier(details)
    assert not success


@pytest.mark.django_db
def test_add_supplier_requires_name():
    details = {"name": "  ", "contact_person": "x"}
    success, _ = supplier_service.add_supplier(details)
    assert not success


@pytest.mark.django_db
def test_update_supplier_changes_fields():
    supplier = Supplier.objects.create(name="Vendor B", is_active=True)
    success, _ = supplier_service.update_supplier(supplier.pk, {"phone": "999"})
    assert success
    supplier.refresh_from_db()
    assert supplier.phone == "999"


@pytest.mark.django_db
def test_update_supplier_invalid_id():
    success, _ = supplier_service.update_supplier(999, {"phone": "000"})
    assert not success


@pytest.mark.django_db
def test_deactivate_and_reactivate_supplier():
    supplier = Supplier.objects.create(name="Vendor C", is_active=True)
    success, _ = supplier_service.deactivate_supplier(supplier.pk)
    assert success
    supplier.refresh_from_db()
    assert supplier.is_active is False
    success, _ = supplier_service.reactivate_supplier(supplier.pk)
    assert success
    supplier.refresh_from_db()
    assert supplier.is_active is True

