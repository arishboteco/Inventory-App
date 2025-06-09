from datetime import datetime
import os
import sys
import pytest
from sqlalchemy import create_engine, event, text

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Fixture to provide in-memory SQLite engine with tables for tests
@pytest.fixture
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def register_now(dbapi_connection, connection_record):
        dbapi_connection.create_function("NOW", 0, lambda: datetime.now().isoformat())

    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                unit TEXT,
                category TEXT,
                sub_category TEXT,
                permitted_departments TEXT,
                reorder_point REAL,
                current_stock REAL,
                notes TEXT,
                is_active BOOLEAN,
                updated_at TEXT
            );
            """
        ))
        conn.execute(text("""
            CREATE TABLE stock_transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                quantity_change REAL,
                transaction_type TEXT,
                user_id TEXT,
                related_mrn TEXT,
                related_po_id INTEGER,
                notes TEXT,
                transaction_date TEXT
            );
        """))
        conn.execute(text(
            """
            CREATE TABLE suppliers (
                supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                notes TEXT,
                is_active BOOLEAN,
                updated_at TEXT
            );
            """
        ))
    return engine
