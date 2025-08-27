"""Form population services for dropdowns and selections."""

import logging
from typing import Dict, List, Tuple, Any, Optional
from functools import lru_cache

from django.db import connection
from django.db.utils import OperationalError

from .supabase_units import get_units
from ..models import Department, Supplier

logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def get_unit_choices() -> List[Tuple[str, str]]:
    """Get available base units for dropdown selection."""
    try:
        units = get_units()
        base_units = list(units.keys())
        return [(unit, unit) for unit in sorted(base_units)]
    except Exception as e:
        logger.warning(f"Could not load units: {e}")
        # Fallback units for development/testing
        return [
            ('kg', 'Kilograms'),
            ('ltr', 'Liters'),
            ('pc', 'Pieces'),
            ('box', 'Boxes'),
            ('pack', 'Packs'),
        ]


@lru_cache(maxsize=None) 
def get_units_map() -> Dict[str, List[str]]:
    """Get units mapping for JavaScript consumption."""
    try:
        return get_units()
    except Exception as e:
        logger.warning(f"Could not load units map: {e}")
        return {
            'kg': ['kg', 'g', 'lb'],
            'ltr': ['ltr', 'ml', 'gallon'],
            'pc': ['pc', 'each', 'dozen'],
            'box': ['box', 'case', 'carton'],
            'pack': ['pack', 'bundle', 'set'],
        }


@lru_cache(maxsize=None)
def get_category_choices() -> List[Tuple[str, str]]:
    """Get available categories for dropdown selection."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT category FROM category ORDER BY category")
            categories = cursor.fetchall()
            return [(cat[0], cat[0]) for cat in categories if cat[0]]
    except OperationalError as e:
        logger.warning(f"Could not load categories: {e}")
        # Fallback categories for development/testing
        return [
            ('Food & Beverage', 'Food & Beverage'),
            ('Raw Materials', 'Raw Materials'),
            ('Packaging', 'Packaging'),
            ('Cleaning Supplies', 'Cleaning Supplies'),
            ('Office Supplies', 'Office Supplies'),
        ]


@lru_cache(maxsize=None)
def get_categories_map() -> Dict[str, List[Dict[str, str]]]:
    """Get category-subcategory mapping for JavaScript consumption."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT category, sub_category FROM category ORDER BY category, sub_category")
            rows = cursor.fetchall()
            
        categories_map = {}
        for category, sub_category in rows:
            if category and sub_category:
                if category not in categories_map:
                    categories_map[category] = []
                categories_map[category].append({'name': sub_category})
        
        return categories_map
    except OperationalError as e:
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
    """Get available subcategories for a given category."""
    try:
        with connection.cursor() as cursor:
            if category:
                cursor.execute(
                    "SELECT DISTINCT sub_category FROM category WHERE category = %s ORDER BY sub_category",
                    [category]
                )
            else:
                cursor.execute("SELECT DISTINCT sub_category FROM category ORDER BY sub_category")
            subcategories = cursor.fetchall()
            return [(subcat[0], subcat[0]) for subcat in subcategories if subcat[0]]
    except OperationalError as e:
        logger.warning(f"Could not load subcategories: {e}")
        return []


def get_department_choices() -> List[Tuple[int, str]]:
    """Get available departments for selection."""
    try:
        departments = Department.objects.filter(permitted_departments__isnull=False).values_list(
            'department_id', 'permitted_departments'
        )
        return [(dept[0], dept[1]) for dept in departments if dept[1]]
    except Exception as e:
        logger.warning(f"Could not load departments: {e}")
        return []


def get_supplier_choices() -> List[Tuple[int, str]]:
    """Get available suppliers for selection."""
    try:
        suppliers = Supplier.objects.filter(is_active=True).values_list('supplier_id', 'name')
        return [(supplier[0], supplier[1]) for supplier in suppliers]
    except Exception as e:
        logger.warning(f"Could not load suppliers: {e}")
        return []


def get_purchase_unit_choices(base_unit: Optional[str] = None) -> List[Tuple[str, str]]:
    """Get available purchase units for a given base unit."""
    if not base_unit:
        return []
    
    try:
        units_map = get_units_map()
        purchase_units = units_map.get(base_unit, [base_unit])
        return [(unit, unit) for unit in purchase_units]
    except Exception as e:
        logger.warning(f"Could not load purchase units for {base_unit}: {e}")
        return [(base_unit, base_unit)] if base_unit else []


# Clear cache functions
def clear_form_caches():
    """Clear all cached form data."""
    get_unit_choices.cache_clear()
    get_units_map.cache_clear()
    get_category_choices.cache_clear()
    get_categories_map.cache_clear()
    get_subcategory_choices.cache_clear()
