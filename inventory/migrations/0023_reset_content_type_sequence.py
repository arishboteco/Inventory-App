from django.db import migrations


def reset_content_type_sequence(apps, schema_editor):
    """Advance the django_content_type PK sequence past the current MAX(id).

    Only runs on PostgreSQL; safe no-op on SQLite / other backends.
    The sequence can fall behind when rows are inserted with explicit IDs
    (e.g. loaddata, database restores). Django's post_migrate create_contenttypes
    then fails with: IntegrityError duplicate key value violates unique constraint
    "django_content_type_pkey".
    """
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        SELECT setval(
            pg_get_serial_sequence('django_content_type', 'id'),
            COALESCE(MAX(id), 1)
        )
        FROM django_content_type;
        """
    )


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0022_stocksnapshot"),
    ]

    operations = [
        migrations.RunPython(reset_content_type_sequence, migrations.RunPython.noop),
    ]
