from django.db import migrations


class Migration(migrations.Migration):
    """
    Make indents.department_id nullable in the actual database.

    Migration 0016 used SeparateDatabaseAndState with empty database_operations,
    meaning it only updated Django's model state but never ran the DDL. The real
    PostgreSQL column was left as NOT NULL (its original schema definition),
    causing an IntegrityError whenever an indent is created without a department
    (e.g. the auto-generated low-stock indent).
    """

    dependencies = [
        ("inventory", "0038_add_performance_indexes"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE indents ALTER COLUMN department_id DROP NOT NULL;",
            reverse_sql="ALTER TABLE indents ALTER COLUMN department_id SET NOT NULL;",
        ),
    ]
