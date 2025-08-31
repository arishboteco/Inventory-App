PRAGMA foreign_keys = ON;

-- Items table: align EXACTLY with the unmanaged model field names
CREATE TABLE IF NOT EXISTS units (
  purchase_unit TEXT NOT NULL,
  base_unit TEXT NOT NULL,
  conversion_factor NUMERIC,
  unit_id INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS category (
  category_id INTEGER PRIMARY KEY,
  category TEXT NOT NULL,
  sub_category TEXT NOT NULL
);

INSERT INTO units (unit_id, purchase_unit, base_unit, conversion_factor) VALUES
  (55, 'PC', 'PC', 1),
  (19, 'KG', 'GM', 1000);

INSERT INTO category (category_id, category, sub_category) VALUES
  (1, 'Grocery', 'General'),
  (2, 'Perishable', 'Fruit');

CREATE TABLE IF NOT EXISTS items (
  item_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  unit_id INTEGER NOT NULL,
  category_id_ref INTEGER,
  initial_purchase_price NUMERIC,
  last_purchase_price NUMERIC,
  preferred_supplier_id INTEGER,
  minimum_order_qty NUMERIC,
  lead_time_days INTEGER,
  permitted_departments TEXT,           -- ✅ add this column (store JSON/string; tests only need presence)
  reorder_point NUMERIC DEFAULT 0,
  current_stock NUMERIC DEFAULT 0,
  notes TEXT,
  is_active BOOLEAN DEFAULT 1,
  updated_at TEXT,
  FOREIGN KEY (unit_id) REFERENCES units(unit_id),
  FOREIGN KEY (category_id_ref) REFERENCES category(category_id)
);

CREATE TABLE IF NOT EXISTS suppliers (
  supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  contact_person TEXT,
  phone TEXT,
  email TEXT,
  address TEXT,
  notes TEXT,
  is_active BOOLEAN DEFAULT 1,
  updated_at TEXT
);

-- Stock transactions: columns used by KPIs + tests
CREATE TABLE IF NOT EXISTS stock_transactions (
  transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER,
  quantity_change NUMERIC,
  transaction_type TEXT,
  user_id TEXT,
  user_id_int INTEGER,
  related_indent_id INTEGER,
  related_po_id INTEGER,
  notes TEXT,
  transaction_date TEXT NOT NULL,
  FOREIGN KEY (item_id) REFERENCES items(item_id)
);
