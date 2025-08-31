"""
Categories Service - Proper Implementation of Category Table Architecture

This service implements the correct category table logic:

1. category_id: Unique identifier for a specific category/sub_category combination
2. category: Primary grouping/classification of items (Grocery, Perishable, etc.)
3. sub_category: Detailed subdivision within category (Dairy, Meat, etc.)

Example records:
- category_id=1: category=Grocery, sub_category=Juices And Purees
- category_id=2: category=Perishable, sub_category=Meat And Poultry
- category_id=3: category=Liquor, sub_category=Tequila

Usage:
- Items store only category_id (foreign key reference)
- Display both category and sub_category for user interface
- Filter by category for broad grouping
- Filter by category_id for specific classification
"""

import logging
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from inventory.models.category import Category

logger = logging.getLogger(__name__)


class CategoriesService:
    """Service for categories and subcategories via the category table."""

    @staticmethod
    @lru_cache(maxsize=None)
    def get_category_info(category_id: int) -> Dict:
        """Get complete category information for a given category_id.

        Returns:
            dict: {
                'category_id': int,
                'category': str,
                'sub_category': str
            }
        """
        try:
            category = Category.objects.get(category_id=category_id)
        except Category.DoesNotExist:
            return {
                'category_id': category_id,
                'category': 'Uncategorized',
                'sub_category': 'General',
            }

        return {
            'category_id': category.category_id,
            'category': category.category,
            'sub_category': category.sub_category,
        }

    @staticmethod
    def get_category_display(category_id: int) -> str:
        """Get the category name for display in UI."""
        category_info = CategoriesService.get_category_info(category_id)
        return category_info['category']

    @staticmethod
    def get_sub_category_display(category_id: int) -> str:
        """Get the sub_category name for display in UI."""
        category_info = CategoriesService.get_category_info(category_id)
        return category_info['sub_category']

    @staticmethod
    def get_full_category_display(category_id: int) -> str:
        """Get the full category display as 'Category > Sub Category'."""
        category_info = CategoriesService.get_category_info(category_id)
        return f"{category_info['category']} > {category_info['sub_category']}"

    @staticmethod
    @lru_cache(maxsize=None)
    def get_all_categories() -> List[Dict]:
        """Get all available categories for dropdown population."""
        categories = Category.objects.all().order_by('category', 'sub_category')
        return [
            {
                'category_id': cat.category_id,
                'category': cat.category,
                'sub_category': cat.sub_category,
            }
            for cat in categories
        ]

    @staticmethod
    def get_categories_by_category(category: str) -> List[Dict]:
        """Get all sub-categories available for a given category."""
        all_categories = CategoriesService.get_all_categories()
        return [cat for cat in all_categories if cat['category'] == category]

    @staticmethod
    def get_unique_categories() -> List[str]:
        """Get list of unique category names."""
        all_categories = CategoriesService.get_all_categories()
        unique_categories = sorted(list(set(cat['category'] for cat in all_categories)))
        return unique_categories

    @staticmethod
    def get_category_choices_for_forms() -> List[Tuple[int, str]]:
        """Get category choices formatted for Django forms (value, label)."""
        all_categories = CategoriesService.get_all_categories()
        return [
            (cat['category_id'], f"{cat['category']} > {cat['sub_category']}")
            for cat in all_categories
        ]

    @staticmethod
    def get_category_choices_grouped() -> Dict[str, List[Tuple[int, str]]]:
        """Get category choices grouped by main category for optgroups."""
        all_categories = CategoriesService.get_all_categories()
        grouped = {}

        for cat in all_categories:
            category_name = cat['category']
            if category_name not in grouped:
                grouped[category_name] = []
            grouped[category_name].append((cat['category_id'], cat['sub_category']))

        return grouped

    @staticmethod
    def find_category_id(category: str, sub_category: str) -> Optional[int]:
        """Find category_id for a given category/sub_category combination."""
        return (
            Category.objects.filter(category=category, sub_category=sub_category)
            .values_list('category_id', flat=True)
            .first()
        )

    @staticmethod
    def find_category_id_by_category_only(category: str) -> Optional[int]:
        """Find first category_id for a given category.

        Use when sub_category doesn't matter.
        """
        return (
            Category.objects.filter(category=category)
            .order_by('sub_category')
            .values_list('category_id', flat=True)
            .first()
        )

    @staticmethod
    def validate_category_id(category_id: int) -> bool:
        """Check if a category_id exists in the category table."""
        category_info = CategoriesService.get_category_info(category_id)
        return category_info['category'] != 'Uncategorized'


# Convenience functions for backward compatibility
def get_category_choices() -> List[Tuple[str, str]]:
    """Legacy function - use CategoriesService.get_unique_categories() instead."""
    categories = CategoriesService.get_unique_categories()
    return [(cat, cat) for cat in categories]


def get_subcategory_choices(category: Optional[str] = None) -> List[Tuple[str, str]]:
    """Legacy function - use CategoriesService.get_categories_by_category() instead."""
    if category:
        subcategories = CategoriesService.get_categories_by_category(category)
        return [
            (subcat['sub_category'], subcat['sub_category'])
            for subcat in subcategories
        ]
    else:
        all_categories = CategoriesService.get_all_categories()
        unique_subcategories = sorted(
            list(set(cat['sub_category'] for cat in all_categories))
        )
        return [(subcat, subcat) for subcat in unique_subcategories]


def get_categories_map() -> Dict[str, List[Dict[str, str]]]:
    """Legacy helper; prefer CategoriesService.get_category_choices_grouped()."""
    grouped = CategoriesService.get_category_choices_grouped()
    return {
        category: [{'name': subcat[1]} for subcat in subcategories]
        for category, subcategories in grouped.items()
    }
