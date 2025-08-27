from django.db import migrations


def rename_notes_to_item_notes(apps, schema_editor):
    table_name = "grn_items"
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
    if "notes" in columns and "item_notes" not in columns:
        schema_editor.execute(
            f"ALTER TABLE {table_name} RENAME COLUMN notes TO item_notes"
        )
    elif "notes" in columns and "item_notes" in columns:
        schema_editor.execute(
            f"UPDATE {table_name} SET item_notes = COALESCE(item_notes, notes)"
        )
        schema_editor.execute(f"ALTER TABLE {table_name} DROP COLUMN notes")


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0006_add_item_notes_to_grnitem"),
    ]

    operations = [
        migrations.RunPython(rename_notes_to_item_notes, migrations.RunPython.noop),
    ]
