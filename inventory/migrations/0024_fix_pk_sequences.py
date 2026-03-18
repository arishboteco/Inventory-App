from django.db import migrations


def reset_pk_sequences(apps, schema_editor):
    """Advance PK sequences for item_departments and recipe_items_new.

    Both tables had rows inserted via fixtures/migrations with explicit IDs,
    leaving their PostgreSQL sequences behind. Subsequent INSERTs collide with
    existing IDs and raise IntegrityError. Only runs on PostgreSQL; no-op on SQLite.
    """
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        SELECT setval(
            pg_get_serial_sequence('item_departments', 'id'),
            COALESCE((SELECT MAX(id) FROM item_departments), 0) + 1,
            false
        );
        SELECT setval(
            pg_get_serial_sequence('recipe_items_new', 'recipe_item_id'),
            COALESCE((SELECT MAX(recipe_item_id) FROM recipe_items_new), 0) + 1,
            false
        );
        """
    )


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0023_reset_content_type_sequence'),
    ]

    operations = [
        migrations.RunPython(reset_pk_sequences, migrations.RunPython.noop),
    ]
