"""
Database Performance Optimization Migration
Adds strategic indexes for frequently used queries
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0003_add_department_models'),
    ]

    operations = [
        # Item table optimizations
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_name_trgm ON inventory_item USING gin (name gin_trgm_ops);",
            reverse_sql="DROP INDEX IF EXISTS idx_items_name_trgm;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_active_stock ON inventory_item (is_active, current_stock) WHERE is_active = true;",
            reverse_sql="DROP INDEX IF EXISTS idx_items_active_stock;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_reorder_check ON inventory_item (current_stock, reorder_point) WHERE is_active = true;",
            reverse_sql="DROP INDEX IF EXISTS idx_items_reorder_check;"
        ),
        
        # Stock transaction optimizations (most frequently queried)
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stock_tx_item_date ON inventory_stocktransaction (item_id, transaction_date DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_stock_tx_item_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stock_tx_type_date ON inventory_stocktransaction (transaction_type, transaction_date DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_stock_tx_type_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stock_tx_user_date ON inventory_stocktransaction (user_id, transaction_date DESC) WHERE user_id IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_stock_tx_user_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stock_tx_date_range ON inventory_stocktransaction (transaction_date DESC, transaction_type, item_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_stock_tx_date_range;"
        ),
        
        # Supplier optimizations
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_suppliers_name_trgm ON inventory_supplier USING gin (name gin_trgm_ops);",
            reverse_sql="DROP INDEX IF EXISTS idx_suppliers_name_trgm;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_suppliers_active_name ON inventory_supplier (is_active, name) WHERE is_active = true;",
            reverse_sql="DROP INDEX IF EXISTS idx_suppliers_active_name;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_suppliers_contact_search ON inventory_supplier (contact_person, email) WHERE is_active = true;",
            reverse_sql="DROP INDEX IF EXISTS idx_suppliers_contact_search;"
        ),
        
        # Sale transaction optimizations
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_date_item ON inventory_saletransaction (sale_date DESC, item_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_sales_date_item;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_date_only ON inventory_saletransaction (date(sale_date) DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_sales_date_only;"
        ),
        
        # Purchase order optimizations  
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_po_status_date ON inventory_purchaseorder (status, order_date DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_po_status_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_po_supplier_date ON inventory_purchaseorder (supplier_id, order_date DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_po_supplier_date;"
        ),
        
        # GRN optimizations
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grn_date_po ON inventory_goodsreceivednote (received_date DESC, purchase_order_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_grn_date_po;"
        ),
        
        # Indent optimizations
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_indent_status_date ON inventory_indent (status, indent_date DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_indent_status_date;"
        ),
        
        # Enable pg_trgm extension for text search if not already enabled
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="-- Cannot safely drop pg_trgm extension"
        ),
    ]
