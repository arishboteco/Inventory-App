from django.db import connection
from inventory.models import Supplier
from inventory.services import supplier_service


def setup_module(module):
    with connection.schema_editor() as editor:
        editor.create_model(Supplier)


def teardown_module(module):
    with connection.schema_editor() as editor:
        editor.delete_model(Supplier)


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


def test_add_supplier_duplicate_name_fails():
    details = {"name": "Dup", "is_active": True}
    supplier_service.add_supplier(details)
    success, _ = supplier_service.add_supplier(details)
    assert not success


def test_add_supplier_requires_name():
    details = {"name": "  ", "contact_person": "x"}
    success, _ = supplier_service.add_supplier(details)
    assert not success


def test_update_supplier_changes_fields():
    supplier = Supplier.objects.create(name="Vendor B", is_active=True)
    success, _ = supplier_service.update_supplier(supplier.pk, {"phone": "999"})
    assert success
    supplier.refresh_from_db()
    assert supplier.phone == "999"


def test_update_supplier_invalid_id():
    success, _ = supplier_service.update_supplier(999, {"phone": "000"})
    assert not success


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


def test_get_all_suppliers_returns_list_of_dicts():
    Supplier.objects.create(name="Vendor D", is_active=True)
    Supplier.objects.create(name="Vendor E", is_active=False)
    active_only = supplier_service.get_all_suppliers()
    assert isinstance(active_only, list)
    assert all(isinstance(row, dict) for row in active_only)
    names = {row["name"] for row in active_only}
    assert "Vendor D" in names and "Vendor E" not in names
    all_suppliers = supplier_service.get_all_suppliers(include_inactive=True)
    names_all = {row["name"] for row in all_suppliers}
    assert {"Vendor D", "Vendor E"}.issubset(names_all)

