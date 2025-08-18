-- Migration: Move data from recipe_items into recipe_components
-- Backs up recipe_items, migrates data, and drops the deprecated table.

BEGIN;

-- Backup the old table for rollback purposes
CREATE TABLE IF NOT EXISTS recipe_items_backup AS TABLE recipe_items;

-- Migrate item components into recipe_components
INSERT INTO recipe_components (
    parent_recipe_id,
    component_kind,
    component_id,
    quantity,
    unit,
    loss_pct,
    sort_order
)
SELECT
    ri.recipe_id AS parent_recipe_id,
    'ITEM' AS component_kind,
    ri.item_id AS component_id,
    ri.quantity,
    i.unit,
    0 AS loss_pct,
    row_number() OVER (PARTITION BY ri.recipe_id ORDER BY ri.recipe_item_id) AS sort_order
FROM recipe_items ri
JOIN items i ON ri.item_id = i.item_id;

-- Drop the deprecated table
DROP TABLE IF EXISTS recipe_items;

COMMIT;
