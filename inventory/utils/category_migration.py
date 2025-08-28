"""
Category Migration Utility

This utility migrates items from using separate category/sub_category text fields
to using proper category_id foreign key references to the category table.

Usage:
    python manage.py shell
    >>> from inventory.utils.category_migration import migrate_item_categories
    >>> migrate_item_categories(dry_run=True)  # Preview changes
    >>> migrate_item_categories(dry_run=False) # Apply changes
"""

from django.db import connection, transaction
from inventory.services.categories_service import CategoriesService
import logging

logger = logging.getLogger(__name__)


def migrate_item_categories(dry_run=True):
    """
    Migrate items from text-based category/sub_category to category_id references.
    
    Args:
        dry_run (bool): If True, only show what would be changed without applying
    """
    print(f"=== CATEGORY MIGRATION {'(DRY RUN)' if dry_run else '(LIVE)'} ===")
    
    with connection.cursor() as cursor:
        # Get all items that have category text but no category_id_ref
        cursor.execute("""
            SELECT item_id, name, category, sub_category, category_id_ref
            FROM items 
            WHERE category IS NOT NULL AND category != ''
            AND (category_id_ref IS NULL OR category_id_ref = 0)
            ORDER BY category, sub_category
        """)
        items_to_migrate = cursor.fetchall()
        
        if not items_to_migrate:
            print("No items need category migration.")
            return
        
        print(f"Found {len(items_to_migrate)} items to migrate:")
        print("item_id | name | category > sub_category | proposed_category_id")
        print("-" * 80)
        
        successful_migrations = []
        failed_migrations = []
        
        for item in items_to_migrate:
            item_id, name, category, sub_category, current_category_id = item
            
            # Find the correct category_id
            if sub_category and sub_category.strip():
                proposed_id = CategoriesService.find_category_id(category, sub_category)
            else:
                proposed_id = CategoriesService.find_category_id_by_category_only(category)
            
            if proposed_id:
                successful_migrations.append({
                    'item_id': item_id,
                    'name': name,
                    'category_id': proposed_id,
                    'category': category,
                    'sub_category': sub_category
                })
                status = "✓"
            else:
                failed_migrations.append({
                    'item_id': item_id,
                    'name': name,
                    'category': category,
                    'sub_category': sub_category
                })
                status = "❌"
            
            display_category = f"{category} > {sub_category or 'None'}"
            print(f"{item_id:7} | {name[:20]:20} | {display_category:25} | {proposed_id or 'None':17} {status}")
        
        print(f"\n=== MIGRATION SUMMARY ===")
        print(f"Successful mappings: {len(successful_migrations)}")
        print(f"Failed mappings: {len(failed_migrations)}")
        
        if failed_migrations:
            print("\nFailed migrations (need manual review):")
            for item in failed_migrations:
                print(f"  - Item {item['item_id']} ({item['name']}): '{item['category']}' > '{item['sub_category']}'")
        
        if not dry_run and successful_migrations:
            print(f"\nApplying {len(successful_migrations)} category_id updates...")
            
            with transaction.atomic():
                for migration in successful_migrations:
                    cursor.execute(
                        "UPDATE items SET category_id_ref = %s WHERE item_id = %s",
                        [migration['category_id'], migration['item_id']]
                    )
                    print(f"  ✓ Updated item {migration['item_id']} -> category_id={migration['category_id']}")
            
            print(f"\nMigration completed successfully!")
            
            # Verify the migration
            print("\n=== VERIFICATION ===")
            cursor.execute("""
                SELECT COUNT(*) FROM items 
                WHERE category IS NOT NULL AND category != ''
                AND category_id_ref IS NOT NULL
            """)
            migrated_count = cursor.fetchone()[0]
            print(f"Items now using category_id_ref: {migrated_count}")
            
        elif dry_run:
            print("\nDry run completed. Use dry_run=False to apply changes.")


def validate_category_migration():
    """Validate that category_id references are working correctly."""
    print("=== CATEGORY MIGRATION VALIDATION ===")
    
    with connection.cursor() as cursor:
        # Check items with category_id_ref
        cursor.execute("""
            SELECT i.item_id, i.name, i.category_id_ref, c.category, c.sub_category
            FROM items i
            LEFT JOIN category c ON i.category_id_ref = c.category_id
            WHERE i.category_id_ref IS NOT NULL
            ORDER BY i.item_id
        """)
        items = cursor.fetchall()
        
        print(f"Found {len(items)} items with category_id references:")
        print("item_id | name | category_id | category > sub_category")
        print("-" * 70)
        
        valid_refs = 0
        invalid_refs = 0
        
        for item in items:
            item_id, name, category_id, category, sub_category = item
            
            if category:  # Valid reference
                valid_refs += 1
                display_category = f"{category} > {sub_category}"
                status = "✓"
            else:  # Invalid reference
                invalid_refs += 1
                display_category = "INVALID REFERENCE"
                status = "❌"
            
            print(f"{item_id:7} | {name[:20]:20} | {category_id:11} | {display_category:30} {status}")
        
        print(f"\nValidation Summary:")
        print(f"Valid references: {valid_refs}")
        print(f"Invalid references: {invalid_refs}")
        
        if invalid_refs == 0:
            print("✓ All category references are valid!")
        else:
            print("❌ Some category references need attention.")


def cleanup_duplicate_category_fields():
    """Clean up the duplicate category/sub_category text fields after successful migration."""
    print("=== CATEGORY FIELD CLEANUP ===")
    print("This will clear the separate category/sub_category text fields")
    print("after confirming all items have valid category_id_ref values.")
    
    with connection.cursor() as cursor:
        # Check that all items with categories have category_id_ref
        cursor.execute("""
            SELECT COUNT(*) FROM items 
            WHERE (category IS NOT NULL AND category != '')
            AND (category_id_ref IS NULL OR category_id_ref = 0)
        """)
        unmigrated = cursor.fetchone()[0]
        
        if unmigrated > 0:
            print(f"❌ Cannot cleanup: {unmigrated} items still need category_id migration")
            return False
        
        # Check that all category_id_ref values are valid
        cursor.execute("""
            SELECT COUNT(*) FROM items i
            LEFT JOIN category c ON i.category_id_ref = c.category_id
            WHERE i.category_id_ref IS NOT NULL AND c.category_id IS NULL
        """)
        invalid_refs = cursor.fetchone()[0]
        
        if invalid_refs > 0:
            print(f"❌ Cannot cleanup: {invalid_refs} items have invalid category_id_ref values")
            return False
        
        print("✓ All category migrations are valid. Safe to cleanup text fields.")
        return True


if __name__ == "__main__":
    # For testing
    migrate_item_categories(dry_run=True)
