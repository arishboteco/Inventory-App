PRAGMA foreign_keys = ON;

-- Items table: align EXACTLY with the unmanaged model field names
CREATE TABLE IF NOT EXISTS items (
  item_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  base_unit TEXT,
  purchase_unit TEXT,
  category_id_ref INTEGER,              -- ✅ was category_id; must be category_id_ref
  permitted_departments TEXT,           -- ✅ add this column (store JSON/string; tests only need presence)
  reorder_point NUMERIC DEFAULT 0,
  current_stock NUMERIC DEFAULT 0,
  notes TEXT,
  is_active BOOLEAN DEFAULT 1,
  updated_at TEXT
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
  item_id INTEGER NOT NULL,
  quantity_change NUMERIC NOT NULL,
  transaction_type TEXT NOT NULL,
  user_id TEXT,
  user_id_int INTEGER,
  related_doc_type TEXT,
  related_doc_id INTEGER,
  notes TEXT,
  transaction_date TEXT NOT NULL,
  FOREIGN KEY (item_id) REFERENCES items(item_id)
);
