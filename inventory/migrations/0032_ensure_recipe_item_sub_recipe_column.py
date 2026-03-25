# Migration 0032: Ensure sub_recipe_id column exists in recipe_items
#
# Migration 0030 was supposed to add this column but the column is missing in
# production, causing 500 errors on any query that reads existing RecipeItem
# rows (food cost report, recipe detail, API, admin list). This migration
# re-applies the DDL idempotently so it is safe to run in any DB state.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0031_recipe_type_binary"),
    ]

    operations = [
        # Ensure sub_recipe_id column exists (idempotent)
        migrations.RunSQL(
            sql="ALTER TABLE recipe_items ADD COLUMN IF NOT EXISTS sub_recipe_id INTEGER;",
            reverse_sql="ALTER TABLE recipe_items DROP COLUMN IF EXISTS sub_recipe_id;",
        ),
        # Ensure item_id is nullable (required for sub-recipe rows)
        migrations.RunSQL(
            sql="ALTER TABLE recipe_items ALTER COLUMN item_id DROP NOT NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
