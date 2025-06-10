-- Rename existing 'unit' column to 'purchase_unit'
ALTER TABLE items RENAME COLUMN unit TO purchase_unit;

-- Add base unit and conversion factor columns if they do not already exist
ALTER TABLE items ADD COLUMN IF NOT EXISTS base_unit TEXT;
ALTER TABLE items ADD COLUMN IF NOT EXISTS conversion_factor REAL;

-- Table for storing unit conversion definitions
CREATE TABLE IF NOT EXISTS units (
    unit_name TEXT PRIMARY KEY,
    base_unit TEXT NOT NULL,
    conversion_factor REAL NOT NULL
);
