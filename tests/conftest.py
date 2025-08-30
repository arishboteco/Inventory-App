import os
import sys

import django
import pytest
from django.db import connection
from django.utils import timezone

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Use our test settings module (module path: inventory_app/settings/test.py)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory_app.settings.test")
django.setup()

from inventory.models import Item, StockTransaction, Supplier, Unit  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def create_test_schema(django_db_setup, django_db_blocker):
    """
    Load a minimal schema into the test DB so unmanaged Supabase models work.
    Runs once per test session AFTER the Django test DB is ready.
    """
    schema_path = os.path.join(PROJECT_ROOT, "tests", "test_schema.sql")
    with django_db_blocker.unblock():
        with open(schema_path, "r") as f:
            sql = f.read()
        # Use executescript on SQLite; otherwise split on semicolons.
        with connection.cursor() as cursor:
            if connection.vendor == "sqlite":
                # Access the native sqlite3 connection to use executescript
                connection.connection.executescript(sql)
            else:
                for stmt in sql.split(";"):
                    if stmt.strip():
                        cursor.execute(stmt)


@pytest.fixture(autouse=True)
def ensure_default_units(db):
    Unit.objects.get_or_create(
        unit_id=55,
        defaults={
            "base_unit": "PC",
            "purchase_unit": "PC",
            "conversion_factor": 1.0,
            "is_default": True,
        },
    )
    Unit.objects.get_or_create(
        unit_id=19,
        defaults={
            "base_unit": "KG",
            "purchase_unit": "KG",
            "conversion_factor": 1.0,
            "is_default": False,
        },
    )


# ---------- FACTORIES ----------

@pytest.fixture
def item_factory(db):
    """
    Factory to create Item objects.
    Usage: item = item_factory(name="Sugar", reorder_point=10, current_stock=5)
    """
    def create_item(**kwargs):
        defaults = {
            "name": "Item",
            "category_id": 1,
            "reorder_point": 0,
            "current_stock": 0,
            "is_active": True,
        }
        defaults.update(kwargs)

        unit = defaults.pop("unit", None)
        unit_id = defaults.pop("unit_id", 19)
        unit_obj, _ = Unit.objects.get_or_create(
            unit_id=unit_id,
            defaults={
                "base_unit": "GM",
                "purchase_unit": "KG",
                "conversion_factor": 1.0,
                "is_default": True if unit_id == 19 else False,
            },
        )
        defaults["unit"] = unit or unit_obj

        return Item.objects.create(**defaults)
    return create_item


@pytest.fixture
def supplier_factory(db):
    """
    Factory to create Supplier objects.
    Usage: supplier = supplier_factory(name="Vendor X")
    """
    def create_supplier(**kwargs):
        defaults = {
            "name": "Vendor",
            "is_active": True,
        }
        defaults.update(kwargs)
        return Supplier.objects.create(**defaults)
    return create_supplier


@pytest.fixture
def stock_txn_factory(db):
    """
    Factory to create StockTransaction rows.
    Usage:
      stock_txn_factory(item=item, quantity_change=5, transaction_type="RECEIVING")
      OR stock_txn_factory(item_id=item.item_id, ...)
    """
    def create_txn(**kwargs):
        assert "item" in kwargs or "item_id" in kwargs, "Provide item or item_id"
        defaults = {
            "quantity_change": 1,
            "transaction_type": "RECEIVING",
            "transaction_date": timezone.now(),
            "notes": "",
        }
        defaults.update(kwargs)
        if "item" in defaults and "item_id" not in defaults:
            defaults["item_id"] = defaults["item"].item_id
        defaults.pop("item", None)
        return StockTransaction.objects.create(**defaults)
    return create_txn


# ---------- AUTO-LOGIN ----------
@pytest.fixture(autouse=True)
def logged_in_client(client, db):
    """
    Log in the default admin user for tests requiring auth.

    We don't call client.logout() during teardown (we use cache-based sessions in tests).
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, _ = User.objects.get_or_create(username="admin")
    if not user.has_usable_password():
        user.set_password("admin")
        user.save()
    client.force_login(user)
    yield
    # No client.logout()
