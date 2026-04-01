from django.db import migrations


class Migration(migrations.Migration):
    """
    Align PostgreSQL NOT NULL constraints with Django model definitions.

    The database was originally created outside Django (Supabase). Many columns
    are NOT NULL in PostgreSQL but the Django models declare them null=True.
    When Django builds an INSERT it includes ALL fields, sending NULL for unset
    ones — bypassing any DB defaults and violating NOT NULL constraints.

    This migration drops NOT NULL on every column where the Django model allows
    null, permanently eliminating this class of IntegrityError.
    """

    dependencies = [
        ("inventory", "0039_indent_department_nullable"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- indents: requested_by is null=True in Django model
                ALTER TABLE indents ALTER COLUMN requested_by DROP NOT NULL;

                -- indent_items: all data columns are null=True in Django model
                ALTER TABLE indent_items ALTER COLUMN indent_id DROP NOT NULL;
                ALTER TABLE indent_items ALTER COLUMN item_id DROP NOT NULL;
                ALTER TABLE indent_items ALTER COLUMN requested_qty DROP NOT NULL;
                ALTER TABLE indent_items ALTER COLUMN issued_qty DROP NOT NULL;
                ALTER TABLE indent_items ALTER COLUMN item_status DROP NOT NULL;

                -- grn_items: item_id is null=True in Django model
                ALTER TABLE grn_items ALTER COLUMN item_id DROP NOT NULL;

                -- stock_transactions: core columns are null=True in Django model
                ALTER TABLE stock_transactions ALTER COLUMN item_id DROP NOT NULL;
                ALTER TABLE stock_transactions ALTER COLUMN quantity_change DROP NOT NULL;
                ALTER TABLE stock_transactions ALTER COLUMN transaction_type DROP NOT NULL;
            """,
            reverse_sql="""
                ALTER TABLE indents ALTER COLUMN requested_by SET NOT NULL;

                ALTER TABLE indent_items ALTER COLUMN indent_id SET NOT NULL;
                ALTER TABLE indent_items ALTER COLUMN item_id SET NOT NULL;
                ALTER TABLE indent_items ALTER COLUMN requested_qty SET NOT NULL;
                ALTER TABLE indent_items ALTER COLUMN issued_qty SET NOT NULL;
                ALTER TABLE indent_items ALTER COLUMN item_status SET NOT NULL;

                ALTER TABLE grn_items ALTER COLUMN item_id SET NOT NULL;

                ALTER TABLE stock_transactions ALTER COLUMN item_id SET NOT NULL;
                ALTER TABLE stock_transactions ALTER COLUMN quantity_change SET NOT NULL;
                ALTER TABLE stock_transactions ALTER COLUMN transaction_type SET NOT NULL;
            """,
        ),
    ]
