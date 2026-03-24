# Migration 0030: apply Phase D DDL that was skipped when 0029 was made state-only
#
# Migration 0029 was incorrectly made fully state-only (database_operations=[])
# to avoid DuplicateColumn errors on source_recipe_id. But the production DB was
# only partially migrated — the recipes.selling_price column and stock_takes /
# stock_take_items tables (and other Phase D columns) do NOT exist.
#
# This migration runs the actual DDL using IF NOT EXISTS / DROP NOT NULL patterns
# so it is safe to run against any state of the production database.

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0029_phase_d_features"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # All operations use RunSQL with IF NOT EXISTS / idempotent patterns.
        # State changes were already applied by 0029 (state-only).
        # ── Columns that may be missing ───────────────────────────────────
        migrations.RunSQL(
            sql="ALTER TABLE goods_received_notes ADD COLUMN IF NOT EXISTS delivery_note_number VARCHAR(100);",
            reverse_sql="ALTER TABLE goods_received_notes DROP COLUMN IF EXISTS delivery_note_number;",
        ),
        migrations.RunSQL(
            # FK references table PK implicitly (PostgreSQL default)
            sql="ALTER TABLE grn_items ADD COLUMN IF NOT EXISTS direct_item_id INTEGER REFERENCES items DEFERRABLE INITIALLY DEFERRED;",
            reverse_sql="ALTER TABLE grn_items DROP COLUMN IF EXISTS direct_item_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE recipes ADD COLUMN IF NOT EXISTS selling_price NUMERIC(10, 2);",
            reverse_sql="ALTER TABLE recipes DROP COLUMN IF EXISTS selling_price;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE recipes ADD COLUMN IF NOT EXISTS target_food_cost_pct NUMERIC(5, 2) DEFAULT 30.0;",
            reverse_sql="ALTER TABLE recipes DROP COLUMN IF EXISTS target_food_cost_pct;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE recipe_items ADD COLUMN IF NOT EXISTS sub_recipe_id INTEGER REFERENCES recipes DEFERRABLE INITIALLY DEFERRED;",
            reverse_sql="ALTER TABLE recipe_items DROP COLUMN IF EXISTS sub_recipe_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE stock_transactions ADD COLUMN IF NOT EXISTS from_department_id INTEGER REFERENCES departments DEFERRABLE INITIALLY DEFERRED;",
            reverse_sql="ALTER TABLE stock_transactions DROP COLUMN IF EXISTS from_department_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE stock_transactions ADD COLUMN IF NOT EXISTS to_department_id INTEGER REFERENCES departments DEFERRABLE INITIALLY DEFERRED;",
            reverse_sql="ALTER TABLE stock_transactions DROP COLUMN IF EXISTS to_department_id;",
        ),
        # ── Make columns nullable (idempotent — no-op if already nullable) ─
        migrations.RunSQL(
            sql="ALTER TABLE goods_received_notes ALTER COLUMN po_id DROP NOT NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="ALTER TABLE grn_items ALTER COLUMN po_item_id DROP NOT NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="ALTER TABLE grn_items ALTER COLUMN quantity_ordered_on_po SET DEFAULT 0;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="ALTER TABLE recipe_items ALTER COLUMN item_id DROP NOT NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        # ── Create Phase D tables (idempotent via IF NOT EXISTS) ──────────
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS stock_takes (
                id          BIGSERIAL PRIMARY KEY,
                date        DATE          NOT NULL,
                status      VARCHAR(20)   NOT NULL DEFAULT 'DRAFT',
                notes       TEXT          NOT NULL DEFAULT '',
                created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMPTZ,
                created_by_id INTEGER NOT NULL REFERENCES auth_user DEFERRABLE INITIALLY DEFERRED,
                department_id INTEGER REFERENCES departments DEFERRABLE INITIALLY DEFERRED
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS stock_take_items; DROP TABLE IF EXISTS stock_takes;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS stock_take_items (
                id           BIGSERIAL PRIMARY KEY,
                system_qty   NUMERIC(10,3) NOT NULL,
                physical_qty NUMERIC(10,3),
                notes        TEXT          NOT NULL DEFAULT '',
                item_id      INTEGER NOT NULL REFERENCES items DEFERRABLE INITIALLY DEFERRED,
                stock_take_id BIGINT NOT NULL REFERENCES stock_takes DEFERRABLE INITIALLY DEFERRED
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS stock_take_items;",
        ),
    ]
