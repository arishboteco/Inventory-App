# Migration 0033: Add missing columns to recipe_items_new (the actual RecipeItem table)
#
# Root cause of the food cost report 500 error:
#
#   RecipeItem.Meta.db_table = "recipe_items_new"
#
# Migration 0029 was state-only (database_operations=[]) so no DDL ran.
# Migrations 0030 and 0032 added sub_recipe_id to "recipe_items" (the old
# deprecated RecipeComponent table), not to "recipe_items_new".
#
# This migration adds the missing columns to the correct table.
# All operations use IF NOT EXISTS / idempotent DDL — safe to run in any state.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0032_ensure_recipe_item_sub_recipe_column"),
    ]

    operations = [
        # Add sub_recipe_id to the correct table
        migrations.RunSQL(
            sql="ALTER TABLE recipe_items_new ADD COLUMN IF NOT EXISTS sub_recipe_id INTEGER;",
            reverse_sql="ALTER TABLE recipe_items_new DROP COLUMN IF EXISTS sub_recipe_id;",
        ),
        # Make item_id nullable (required for sub-recipe rows where item is NULL)
        migrations.RunSQL(
            sql="ALTER TABLE recipe_items_new ALTER COLUMN item_id DROP NOT NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
