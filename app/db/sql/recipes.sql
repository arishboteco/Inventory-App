-- SQL script for recipe tables
CREATE TABLE IF NOT EXISTS recipes (
    recipe_id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE recipes
    ADD COLUMN IF NOT EXISTS type TEXT,
    ADD COLUMN IF NOT EXISTS default_yield_qty NUMERIC,
    ADD COLUMN IF NOT EXISTS default_yield_unit TEXT,
    ADD COLUMN IF NOT EXISTS plating_notes TEXT,
    ADD COLUMN IF NOT EXISTS tags JSONB,
    ADD COLUMN IF NOT EXISTS version INTEGER,
    ADD COLUMN IF NOT EXISTS effective_from TIMESTAMP,
    ADD COLUMN IF NOT EXISTS effective_to TIMESTAMP;

CREATE TABLE IF NOT EXISTS recipe_items (
    recipe_item_id SERIAL PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    quantity REAL NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (recipe_id, item_id)
);

-- Table to store components for recipes (items or sub-recipes)
CREATE TABLE IF NOT EXISTS recipe_components (
    id SERIAL PRIMARY KEY,
    parent_recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    component_kind TEXT NOT NULL CHECK (component_kind IN ('ITEM', 'RECIPE')),
    component_id INTEGER NOT NULL,
    quantity NUMERIC,
    unit TEXT,
    loss_pct NUMERIC DEFAULT 0,
    sort_order INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (parent_recipe_id, component_kind, component_id)
);

-- Trigger function to enforce component_id references based on component_kind
CREATE OR REPLACE FUNCTION check_recipe_component_fk()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.component_kind = 'ITEM' THEN
        PERFORM 1 FROM items WHERE item_id = NEW.component_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Component item % does not exist', NEW.component_id;
        END IF;
    ELSIF NEW.component_kind = 'RECIPE' THEN
        PERFORM 1 FROM recipes WHERE recipe_id = NEW.component_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Component recipe % does not exist', NEW.component_id;
        END IF;
    ELSE
        RAISE EXCEPTION 'Invalid component_kind: %', NEW.component_kind;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_recipe_component_fk
BEFORE INSERT OR UPDATE ON recipe_components
FOR EACH ROW EXECUTE FUNCTION check_recipe_component_fk();

-- Trigger function to prevent circular references among recipes
CREATE OR REPLACE FUNCTION prevent_recipe_cycle()
RETURNS TRIGGER AS $$
DECLARE
    v_found INTEGER;
BEGIN
    IF NEW.component_kind = 'RECIPE' THEN
        -- Check for direct self-reference
        IF NEW.parent_recipe_id = NEW.component_id THEN
            RAISE EXCEPTION 'Circular recipe reference detected';
        END IF;
        WITH RECURSIVE deps AS (
            SELECT rc.component_id
            FROM recipe_components rc
            WHERE rc.parent_recipe_id = NEW.component_id AND rc.component_kind = 'RECIPE'
            UNION
            SELECT rc.component_id
            FROM recipe_components rc
            JOIN deps d ON rc.parent_recipe_id = d.component_id
            WHERE rc.component_kind = 'RECIPE'
        )
        SELECT 1 INTO v_found FROM deps WHERE component_id = NEW.parent_recipe_id LIMIT 1;
        IF v_found IS NOT NULL THEN
            RAISE EXCEPTION 'Circular recipe reference detected';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_recipe_cycle
BEFORE INSERT OR UPDATE ON recipe_components
FOR EACH ROW EXECUTE FUNCTION prevent_recipe_cycle();
