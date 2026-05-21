from django.db import migrations, models


def _table_exists(connection, table_name):
    with connection.cursor() as cursor:
        return table_name in connection.introspection.table_names(cursor)


def _column_exists(connection, table_name, column_name):
    with connection.cursor() as cursor:
        columns = connection.introspection.get_table_description(cursor, table_name)
    return any(column.name == column_name for column in columns)


def ensure_grn_number(apps, schema_editor):
    connection = schema_editor.connection
    table = "goods_received_notes"
    if not _table_exists(connection, table):
        return

    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE goods_received_notes
                ADD COLUMN IF NOT EXISTS grn_number varchar(100)
                """)
            cursor.execute("""
                WITH duplicate_numbers AS (
                    SELECT grn_number
                    FROM goods_received_notes
                    WHERE grn_number IS NOT NULL AND grn_number <> ''
                    GROUP BY grn_number
                    HAVING COUNT(*) > 1
                )
                UPDATE goods_received_notes
                SET grn_number = 'GRN-' || lpad(grn_id::text, 4, '0')
                WHERE grn_number IS NULL
                   OR grn_number = ''
                   OR grn_number IN (SELECT grn_number FROM duplicate_numbers)
                """)
            cursor.execute("""
                ALTER TABLE goods_received_notes
                ALTER COLUMN grn_number SET NOT NULL
                """)
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                    goods_received_notes_grn_number_uniq
                ON goods_received_notes (grn_number)
                """)
        return

    if not _column_exists(connection, table, "grn_number"):
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE goods_received_notes ADD COLUMN grn_number varchar(100)"
            )

    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE goods_received_notes
            SET grn_number = 'GRN-' || printf('%04d', grn_id)
            WHERE grn_number IS NULL OR grn_number = ''
            """)
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                goods_received_notes_grn_number_uniq
            ON goods_received_notes (grn_number)
            """)


def ensure_sales_transactions(apps, schema_editor):
    SaleTransaction = apps.get_model("inventory", "SaleTransaction")
    if _table_exists(schema_editor.connection, SaleTransaction._meta.db_table):
        return
    schema_editor.create_model(SaleTransaction)


def repair_status_defaults(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        if _table_exists(connection, "purchase_orders"):
            cursor.execute("""
                UPDATE purchase_orders
                SET status = CASE status
                    WHEN 'Draft' THEN 'DRAFT'
                    WHEN 'Sent to Supplier' THEN 'SENT'
                    WHEN 'Sent' THEN 'SENT'
                    WHEN 'Received' THEN 'RECEIVED'
                    WHEN 'Cancelled' THEN 'CANCELLED'
                    ELSE status
                END
                WHERE status IN (
                    'Draft', 'Sent to Supplier', 'Sent', 'Received', 'Cancelled'
                )
                """)
        if _table_exists(connection, "indents"):
            cursor.execute("""
                UPDATE indents
                SET status = CASE status
                    WHEN 'Pending' THEN 'PENDING'
                    WHEN 'Submitted' THEN 'SUBMITTED'
                    WHEN 'Processing' THEN 'PROCESSING'
                    WHEN 'Approved' THEN 'APPROVED'
                    WHEN 'Completed' THEN 'COMPLETED'
                    WHEN 'Cancelled' THEN 'CANCELLED'
                    ELSE status
                END
                WHERE status IN (
                    'Pending', 'Submitted', 'Processing', 'Approved',
                    'Completed', 'Cancelled'
                )
                """)
        if _table_exists(connection, "indent_items"):
            cursor.execute("""
                UPDATE indent_items
                SET item_status = CASE item_status
                    WHEN 'Pending Issue' THEN 'PENDING'
                    WHEN 'Pending' THEN 'PENDING'
                    WHEN 'Issued' THEN 'ISSUED'
                    WHEN 'Cancelled' THEN 'CANCELLED'
                    ELSE item_status
                END
                WHERE item_status IN (
                    'Pending Issue', 'Pending', 'Issued', 'Cancelled'
                )
                """)

        if connection.vendor == "postgresql":
            cursor.execute(
                "ALTER TABLE purchase_orders ALTER COLUMN status SET DEFAULT 'DRAFT'"
            )
            cursor.execute(
                "ALTER TABLE indents ALTER COLUMN status SET DEFAULT 'SUBMITTED'"
            )
            cursor.execute(
                "ALTER TABLE indent_items ALTER COLUMN item_status SET DEFAULT 'PENDING'"
            )


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0042_vendor_item_price"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(ensure_grn_number, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="goodsreceivednote",
                    name="grn_number",
                    field=models.CharField(
                        blank=True, default="", max_length=100, unique=True
                    ),
                ),
            ],
        ),
        migrations.RunPython(
            ensure_sales_transactions,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            repair_status_defaults,
            migrations.RunPython.noop,
        ),
    ]
