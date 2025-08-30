"""Form population services for dropdowns and selections."""

import logging
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from django.db import DatabaseError, connection
from django.db.utils import OperationalError

from ..models import Department, Supplier
from .supabase_units import get_units

logger = logging.getLogger(__name__)


class FormService:
    """Service for populating form dropdown options"""

    @staticmethod
    @lru_cache(maxsize=None)
    def get_base_unit_choices() -> Tuple[Tuple[str, str], ...]:
        """Get base unit choices from database"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT DISTINCT base_unit FROM units
                    WHERE base_unit IS NOT NULL
                    ORDER BY base_unit
                    """
                )
                units = cursor.fetchall()
                return tuple((unit[0], unit[0]) for unit in units if unit[0])
        except OperationalError as e:
            logger.warning(f"Could not load base units from database: {e}")
            return (
                ('GM', 'GM'),
                ('ML', 'ML'),
                ('MT', 'MT'),
                ('PC', 'PC'),
            )

    @staticmethod
    @lru_cache(maxsize=None)
    def get_purchase_unit_choices(base_unit: Optional[str] = None) -> Tuple[Tuple[str, str], ...]:
        """Get purchase unit choices, optionally filtered by base_unit"""
        try:
            with connection.cursor() as cursor:
                if base_unit:
                    # Get purchase units for a specific base unit
                    cursor.execute(
                        """
                        SELECT DISTINCT purchase_unit FROM units
                        WHERE base_unit = %s AND purchase_unit IS NOT NULL
                        ORDER BY purchase_unit
                        """,
                        [base_unit],
                    )
                else:
                    # Get all purchase units
                    cursor.execute(
                        """
                        SELECT DISTINCT purchase_unit FROM units
                        WHERE purchase_unit IS NOT NULL
                        ORDER BY purchase_unit
                        """
                    )
                units = cursor.fetchall()
                return tuple((unit[0], unit[0]) for unit in units if unit[0])
        except OperationalError as e:
            logger.warning(f"Could not load purchase units from database: {e}")
            return (
                ('GM', 'GM'),
                ('ML', 'ML'),
                ('MT', 'MT'),
                ('PC', 'PC'),
            )

    @staticmethod
    def get_unit_choices() -> Tuple[Tuple[str, str], ...]:
        """Legacy method for backward compatibility"""
        return FormService.get_base_unit_choices()


@lru_cache(maxsize=None)
def get_units_map() -> Dict[str, List[str]]:
    """Get units mapping for JavaScript consumption."""
    return get_units()


@lru_cache(maxsize=None)
def get_category_choices() -> List[Tuple[str, str]]:
    """Get available categories for dropdown selection.

    This function maintains backward compatibility but delegates to CategoriesService.
    For new code, use CategoriesService.get_unique_categories() directly.
    """
    from .categories_service import CategoriesService
    categories = CategoriesService.get_unique_categories()
    return [(cat, cat) for cat in categories]


@lru_cache(maxsize=None)
def get_categories_map() -> Dict[str, List[Dict[str, str]]]:
    """Get category-subcategory mapping for JavaScript consumption.

    This function maintains backward compatibility but delegates to CategoriesService.
    For new code, use CategoriesService.get_category_choices_grouped() directly.
    """
    from .categories_service import CategoriesService
    try:
        grouped = CategoriesService.get_category_choices_grouped()
        return {
            category: [{'name': subcat[1]} for subcat in subcategories]
            for category, subcategories in grouped.items()
        }
    except DatabaseError as e:
        logger.warning(f"Could not load categories map: {e}")
        # Fallback for development/testing
        return {
            'Food & Beverage': [
                {'name': 'Dairy'},
                {'name': 'Meat'},
                {'name': 'Vegetables'}
            ],
            'Raw Materials': [
                {'name': 'Flour'},
                {'name': 'Sugar'},
                {'name': 'Oil'}
            ],
            'Packaging': [
                {'name': 'Containers'},
                {'name': 'Labels'},
                {'name': 'Bags'}
            ],
        }


@lru_cache(maxsize=None)
def get_subcategory_choices(category: Optional[str] = None) -> List[Tuple[str, str]]:
    """Get available subcategories for a given category.

    This function maintains backward compatibility but delegates to CategoriesService.
    For new code, use CategoriesService.get_categories_by_category() directly.
    """
    from .categories_service import CategoriesService
    try:
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
    except DatabaseError as e:
        logger.warning(f"Could not load subcategories: {e}")
        return []


def get_department_choices() -> List[Tuple[int, str]]:
    """Get available departments for selection."""
    try:
        departments = Department.objects.filter(name__isnull=False).values_list(
            'department_id', 'name'
        )
        return [(dept[0], dept[1]) for dept in departments if dept[1]]
    except DatabaseError as e:
        logger.warning(f"Could not load departments: {e}")
        return []


def get_supplier_choices() -> List[Tuple[int, str]]:
    """Get available suppliers for selection."""
    try:
        suppliers = Supplier.objects.filter(is_active=True).values_list(
            'supplier_id', 'name'
        )
        return [(supplier[0], supplier[1]) for supplier in suppliers]
    except DatabaseError as e:
        logger.warning(f"Could not load suppliers: {e}")
        return []


def get_purchase_unit_choices(base_unit: Optional[str] = None) -> List[Tuple[str, str]]:
    """Get available purchase units for a given base unit."""
    if not base_unit:
        return []

    units_map = get_units_map()
    purchase_units = units_map.get(base_unit, [base_unit])
    return [(unit, unit) for unit in purchase_units]


# Clear cache functions
def clear_form_caches():
    """Clear all cached form data."""
    try:
        FormService.get_base_unit_choices.cache_clear()
        FormService.get_purchase_unit_choices.cache_clear()
        get_units_map.cache_clear()
        get_category_choices.cache_clear()
        get_categories_map.cache_clear()
        get_subcategory_choices.cache_clear()
    except AttributeError:
        # Cache methods may not exist if not decorated
        pass
