-- Rollback: Restore recipe_items from backup and remove migrated components
BEGIN;

-- Remove components that originated from recipe_items
DELETE FROM recipe_components
WHERE component_kind = 'ITEM';

-- Restore the backup of recipe_items
ALTER TABLE IF EXISTS recipe_items_backup RENAME TO recipe_items;

COMMIT;
