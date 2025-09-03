"""
Database Performance Optimization Migration
Adds strategic indexes for frequently used queries
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0003_add_department_models"),
    ]

    # Disable atomic transactions for this migration to allow index creation
    atomic = False

    operations = [
        # First ensure pg_trgm extension exists
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="-- Extension will remain",
        ),
        # Item table optimizations (db_table: "items") - only if table exists
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'items'
                ) THEN
                    CREATE INDEX IF NOT EXISTS idx_items_name_trgm
                    ON items USING gin (name gin_trgm_ops);
                END IF;
            END $$;
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_items_name_trgm;",
        ),
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'items'
                ) THEN
                    CREATE INDEX IF NOT EXISTS idx_items_active_stock
                    ON items (is_active, current_stock)
                    WHERE is_active = true;
                END IF;
            END $$;
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_items_active_stock;",
        ),
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'items'
                ) THEN
                    CREATE INDEX IF NOT EXISTS idx_items_reorder_check
                    ON items (current_stock, reorder_point)
                    WHERE is_active = true;
                END IF;
            END $$;
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_items_reorder_check;",
        ),
        # Stock transaction optimizations (db_table: "stock_transactions") -
        # only if table exists
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'stock_transactions'
                ) THEN
                    CREATE INDEX IF NOT EXISTS idx_stock_tx_item_date
                    ON stock_transactions (
                        item_id,
                        transaction_date DESC
                    );
                END IF;
            END $$;
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_stock_tx_item_date;",
        ),
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'stock_transactions'
                ) THEN
                    CREATE INDEX IF NOT EXISTS idx_stock_tx_type_date
                    ON stock_transactions (
                        transaction_type,
                        transaction_date DESC
                    );
                END IF;
            END $$;
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_stock_tx_type_date;",
        ),
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'stock_transactions'
                ) THEN
                    CREATE INDEX IF NOT EXISTS idx_stock_tx_user_date
                    ON stock_transactions (
                        user_id,
                        transaction_date DESC
                    )
                    WHERE user_id IS NOT NULL;
                END IF;
            END $$;
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_stock_tx_user_date;",
        ),
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'stock_transactions'
                ) THEN
                    CREATE INDEX IF NOT EXISTS idx_stock_tx_date_range
                    ON stock_transactions (
                        transaction_date DESC,
                        transaction_type,
                        item_id
                    );
                END IF;
            END $$;
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_stock_tx_date_range;",
        ),
        # Supplier optimizations (db_table: "suppliers") - only if table exists
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'suppliers'
                ) THEN
                    CREATE INDEX IF NOT EXISTS idx_suppliers_name_trgm
                    ON suppliers USING gin (name gin_trgm_ops);
                END IF;
            END $$;
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_suppliers_name_trgm;",
        ),
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'suppliers'
                ) THEN
                    CREATE INDEX IF NOT EXISTS idx_suppliers_active_name
                    ON suppliers (is_active, name)
                    WHERE is_active = true;
                END IF;
            END $$;
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_suppliers_active_name;",
        ),
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'suppliers'
                ) THEN
                    CREATE INDEX IF NOT EXISTS idx_suppliers_contact_search
                    ON suppliers (contact_person, email)
                    WHERE is_active = true;
                END IF;
            END $$;
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_suppliers_contact_search;",
        ),
        # Only create indexes for tables that exist - skip optional tables for now.
        # We'll create a follow-up migration for additional tables once they're
        # confirmed to exist.
    ]
