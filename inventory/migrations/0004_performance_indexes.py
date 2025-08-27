"""
Database Performance Optimization Migration
Adds strategic indexes for frequently used queries
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0003_add_department_models'),
    ]
    
    # Disable atomic transactions for this migration to allow index creation
    atomic = False

    operations = [
        # First ensure pg_trgm extension exists
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="-- Extension will remain"
        ),
        
        # Item table optimizations (db_table: "items")
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_items_name_trgm ON items USING gin (name gin_trgm_ops);",
            reverse_sql="DROP INDEX IF EXISTS idx_items_name_trgm;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_items_active_stock ON items (is_active, current_stock) WHERE is_active = true;",
            reverse_sql="DROP INDEX IF EXISTS idx_items_active_stock;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_items_reorder_check ON items (current_stock, reorder_point) WHERE is_active = true;",
            reverse_sql="DROP INDEX IF EXISTS idx_items_reorder_check;"
        ),
        
        # Stock transaction optimizations (db_table: "stock_transactions")
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_stock_tx_item_date ON stock_transactions (item_id, transaction_date DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_stock_tx_item_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_stock_tx_type_date ON stock_transactions (transaction_type, transaction_date DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_stock_tx_type_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_stock_tx_user_date ON stock_transactions (user_id, transaction_date DESC) WHERE user_id IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_stock_tx_user_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_stock_tx_date_range ON stock_transactions (transaction_date DESC, transaction_type, item_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_stock_tx_date_range;"
        ),
        
        # Supplier optimizations (db_table: "suppliers")
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_suppliers_name_trgm ON suppliers USING gin (name gin_trgm_ops);",
            reverse_sql="DROP INDEX IF EXISTS idx_suppliers_name_trgm;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_suppliers_active_name ON suppliers (is_active, name) WHERE is_active = true;",
            reverse_sql="DROP INDEX IF EXISTS idx_suppliers_active_name;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_suppliers_contact_search ON suppliers (contact_person, email) WHERE is_active = true;",
            reverse_sql="DROP INDEX IF EXISTS idx_suppliers_contact_search;"
        ),
        
        # Sale transaction optimizations (db_table: "sales_transactions")
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_sales_date_item ON sales_transactions (sale_date DESC, item_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_sales_date_item;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_sales_date_only ON sales_transactions (date(sale_date) DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_sales_date_only;"
        ),
        
        # Purchase order optimizations (db_table: "purchase_orders")
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_po_status_date ON purchase_orders (status, order_date DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_po_status_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_po_supplier_date ON purchase_orders (supplier_id, order_date DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_po_supplier_date;"
        ),
        
        # GRN optimizations (db_table: "goods_received_notes")
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_grn_date_po ON goods_received_notes (received_date DESC, purchase_order_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_grn_date_po;"
        ),
        
        # Indent optimizations (db_table: "indents")
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_indent_status_date ON indents (status, indent_date DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_indent_status_date;"
        ),
    ]
