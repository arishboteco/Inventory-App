from sqlalchemy import text

from app.services import supplier_service



def test_add_supplier_inserts_row(sqlite_engine):
    details = {
        "name": "Vendor A",
        "contact_person": "John",
        "phone": "123",
        "email": "john@example.com",
        "address": "Addr",
        "notes": "Note",
        "is_active": True,
    }
    success, msg = supplier_service.add_supplier(sqlite_engine, details)
    assert success

    with sqlite_engine.connect() as conn:
        row = conn.execute(text("SELECT name FROM suppliers WHERE name='Vendor A'"))
        assert row.fetchone() is not None


def test_add_supplier_duplicate_name_fails(sqlite_engine):
    details = {"name": "Dup", "is_active": True}
    supplier_service.add_supplier(sqlite_engine, details)
    success, msg = supplier_service.add_supplier(sqlite_engine, details)
    assert not success


def test_add_supplier_requires_name(sqlite_engine):
    details = {
        "name": "  ",
        "contact_person": "x",
    }
    success, msg = supplier_service.add_supplier(sqlite_engine, details)
    assert not success


def test_update_supplier_changes_fields(sqlite_engine):
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO suppliers (name, is_active) VALUES ('Vendor B', 1)"
            )
        )
        supplier_id = conn.execute(text("SELECT supplier_id FROM suppliers WHERE name='Vendor B'"))
        supplier_id = supplier_id.scalar_one()

    success, msg = supplier_service.update_supplier(sqlite_engine, supplier_id, {"phone": "999"})
    assert success

    with sqlite_engine.connect() as conn:
        phone = conn.execute(text("SELECT phone FROM suppliers WHERE supplier_id=:i"), {"i": supplier_id}).scalar_one()
        assert phone == "999"


def test_update_supplier_invalid_id(sqlite_engine):
    success, msg = supplier_service.update_supplier(sqlite_engine, 999, {"phone": "000"})
    assert not success


def test_deactivate_and_reactivate_supplier(sqlite_engine):
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO suppliers (name, is_active) VALUES ('Vendor C', 1)"
            )
        )
        supplier_id = conn.execute(text("SELECT supplier_id FROM suppliers WHERE name='Vendor C'"))
        supplier_id = supplier_id.scalar_one()

    success, _ = supplier_service.deactivate_supplier(sqlite_engine, supplier_id)
    assert success
    with sqlite_engine.connect() as conn:
        active = conn.execute(text("SELECT is_active FROM suppliers WHERE supplier_id=:i"), {"i": supplier_id}).scalar_one()
        assert active == 0

    success, _ = supplier_service.reactivate_supplier(sqlite_engine, supplier_id)
    assert success
    with sqlite_engine.connect() as conn:
        active = conn.execute(text("SELECT is_active FROM suppliers WHERE supplier_id=:i"), {"i": supplier_id}).scalar_one()
        assert active == 1

