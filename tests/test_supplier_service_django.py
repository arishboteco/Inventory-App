import pytest

from django.urls import reverse

from inventory.models import Supplier
from inventory.services import supplier_service


@pytest.mark.django_db
def test_add_supplier_inserts_row():
    details = {"name": "Vendor A", "is_active": True}
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
    ok, _ = supplier_service.deactivate_supplier(supplier.pk)
    assert ok
    supplier.refresh_from_db()
    assert supplier.is_active is False
    ok, _ = supplier_service.reactivate_supplier(supplier.pk)
    assert ok
    supplier.refresh_from_db()
    assert supplier.is_active is True


@pytest.mark.django_db
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


@pytest.mark.django_db
def test_suppliers_table_filters(client):
    Supplier.objects.create(name="Alpha", is_active=True)
    Supplier.objects.create(name="Beta", is_active=False)
    url = reverse("suppliers_table")
    resp = client.get(url, {"q": "Alpha", "active": "1"})
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Alpha" in content
    assert "Beta" not in content


@pytest.mark.django_db
def test_suppliers_export(client):
    Supplier.objects.create(name="Act", is_active=True)
    Supplier.objects.create(name="Inact", is_active=False)
    url = reverse("suppliers_table")
    resp = client.get(url, {"active": "0", "export": "1"})
    assert resp.status_code == 200
    assert resp["Content-Type"] == "text/csv"
    body = resp.content.decode()
    assert "Inact" in body
    assert "Act," not in body


@pytest.mark.django_db
def test_toggle_supplier_post(client):
    supplier = Supplier.objects.create(name="ToggleMe", is_active=True)
    url = reverse("supplier_toggle_active", args=[supplier.pk])
    resp = client.post(url, {"page": "1"})
    assert resp.status_code == 200
    supplier.refresh_from_db()
    assert supplier.is_active is False
    resp = client.post(url, {"page": "1"})
    assert resp.status_code == 200
    supplier.refresh_from_db()
    assert supplier.is_active is True
