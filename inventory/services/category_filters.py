import logging
from typing import Any, Dict, List

from .supabase_categories import get_categories as get_supabase_categories

logger = logging.getLogger(__name__)


def resolve_category_filters(request) -> Dict[str, Any]:
    """Return selected category values and available options from actual database."""
    from ..models import Item, Department
    
    category = (request.GET.get("category") or "").strip()
    subcategory = (request.GET.get("subcategory") or "").strip()
    base_unit = (request.GET.get("base_unit") or "").strip()
    department = (request.GET.get("department") or "").strip()

    # Get actual categories from database
    categories = list(Item.objects.exclude(category__isnull=True).exclude(category="").values_list('category', flat=True).distinct().order_by('category'))
    
    # Get subcategories based on selected category
    subcategories_qs = Item.objects.exclude(sub_category__isnull=True).exclude(sub_category="")
    if category:
        subcategories_qs = subcategories_qs.filter(category=category)
    subcategories = list(subcategories_qs.values_list('sub_category', flat=True).distinct().order_by('sub_category'))
    
    # Get base units from database
    base_units = list(Item.objects.exclude(base_unit__isnull=True).exclude(base_unit="").values_list('base_unit', flat=True).distinct().order_by('base_unit'))
    
    # Get departments
    departments = list(Department.objects.all().values_list('name', flat=True).order_by('name'))

    return {
        "category": category,
        "subcategory": subcategory,
        "base_unit": base_unit,
        "department": department,
        "categories": categories,
        "subcategories": subcategories,
        "base_units": base_units,
        "departments": departments,
    }


def build_filters(request) -> List[Dict[str, Any]]:
    """Build filter UI elements based on request parameters."""
    resolved = resolve_category_filters(request)
    
    category_options = [{"value": "", "label": "All Categories"}]
    category_options.extend([{"value": c, "label": c} for c in resolved["categories"]])
    
    subcategory_options = [{"value": "", "label": "All Subcategories"}]
    subcategory_options.extend([{"value": c, "label": c} for c in resolved["subcategories"]])
    
    base_unit_options = [{"value": "", "label": "All Units"}]
    base_unit_options.extend([{"value": u, "label": u} for u in resolved["base_units"]])
    
    department_options = [{"value": "", "label": "All Departments"}]
    department_options.extend([{"value": d, "label": d} for d in resolved["departments"]])
    
    return [
        {
            "name": "category",
            "label": "Category",
            "value": resolved["category"],
            "options": category_options
        },
        {
            "name": "subcategory",
            "label": "Subcategory", 
            "value": resolved["subcategory"],
            "options": subcategory_options
        },
        {
            "name": "base_unit",
            "label": "Unit",
            "value": resolved["base_unit"],
            "options": base_unit_options
        },
        {
            "name": "department",
            "label": "Department",
            "value": resolved["department"],
            "options": department_options
        }
    ]
