-- SQL script for menu items table
CREATE TABLE IF NOT EXISTS menu_items (
    menu_item_id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL UNIQUE REFERENCES items(item_id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
