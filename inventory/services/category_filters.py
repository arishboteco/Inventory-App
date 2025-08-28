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
    categories_flat = list(Item.objects.exclude(category__isnull=True).exclude(category="").values_list('category', flat=True).distinct().order_by('category'))
    categories = [(c, c) for c in categories_flat]
    
    # Get subcategories based on selected category
    subcategories_qs = Item.objects.exclude(sub_category__isnull=True).exclude(sub_category="")
    if category:
        subcategories_qs = subcategories_qs.filter(category=category)
    subcategories_flat = list(subcategories_qs.values_list('sub_category', flat=True).distinct().order_by('sub_category'))
    subcategories = [(c, c) for c in subcategories_flat]
    
    # Get base units from database
    base_units_flat = list(Item.objects.exclude(base_unit__isnull=True).exclude(base_unit="").values_list('base_unit', flat=True).distinct().order_by('base_unit'))
    base_units = [(u, u) for u in base_units_flat]
    
    # Get departments
    departments_flat = list(Department.objects.all().values_list('name', flat=True).order_by('name'))
    departments = [(d, d) for d in departments_flat]

    return {
        "category": category,
        "subcategory": subcategory,
        "base_unit": base_unit,
        "department": department,
        "categories": categories,
        "subcategories": subcategories,
        "base_units": base_units,
        "units": base_units,  # Template expects 'units'
        "departments": departments,
    }


def build_filters(request) -> List[Dict[str, Any]]:
    """Build filter UI elements based on request parameters."""
    resolved = resolve_category_filters(request)
    
    category_options = [{"value": "", "label": "All Categories"}]
    category_options.extend([{"value": c[0], "label": c[1]} for c in resolved["categories"]])
    
    subcategory_options = [{"value": "", "label": "All Subcategories"}]
    subcategory_options.extend([{"value": c[0], "label": c[1]} for c in resolved["subcategories"]])
    
    base_unit_options = [{"value": "", "label": "All Units"}]
    base_unit_options.extend([{"value": u[0], "label": u[1]} for u in resolved["base_units"]])
    
    department_options = [{"value": "", "label": "All Departments"}]
    department_options.extend([{"value": d[0], "label": d[1]} for d in resolved["departments"]])
    
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
