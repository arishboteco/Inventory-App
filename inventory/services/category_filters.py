"""Category and department filter helpers."""

import logging
from typing import Any, Dict, List

from .categories_service import CategoriesService

logger = logging.getLogger(__name__)


def resolve_category_filters(request) -> Dict[str, Any]:
    """Return selected category values and available options."""
    from ..models import Department

    category = (request.GET.get("category") or "").strip()
    subcategory = (request.GET.get("subcategory") or "").strip()
    department = (request.GET.get("department") or "").strip()

    try:
        categories_map = CategoriesService.get_category_choices_grouped()
    except Exception:  # pragma: no cover - defensive
        logger.debug("CategoriesService unavailable; returning empty lists")
        categories_map = {}

    categories = list(categories_map.keys())
    subcats = categories_map.get(category, [])
    subcategories = [sc[1] for sc in subcats]

    departments = list(
        Department.objects.all().values_list("name", flat=True).order_by("name")
    )

    return {
        "category": category,
        "subcategory": subcategory,
        "base_unit": "",
        "department": department,
        "categories": categories,
        "subcategories": subcategories,
        "base_units": [],
        "units": [],
        "departments": [(d, d) for d in departments],
    }


def build_filters(request) -> List[Dict[str, Any]]:
    """Build filter UI elements based on request parameters."""
    resolved = resolve_category_filters(request)

    category_options = [{"value": "", "label": "All Categories"}]
    for c in resolved["categories"]:
        category_options.append({"value": c, "label": c})

    subcategory_options = [{"value": "", "label": "All Subcategories"}]
    for c in resolved["subcategories"]:
        subcategory_options.append({"value": c, "label": c})

    department_options = [{"value": "", "label": "All Departments"}]
    department_options.extend(
        [{"value": d, "label": d} for d in resolved["departments"]]
    )

    return [
        {
            "name": "category",
            "label": "Category",
            "value": resolved["category"],
            "options": category_options,
        },
        {
            "name": "subcategory",
            "label": "Subcategory",
            "value": resolved["subcategory"],
            "options": subcategory_options,
        },
        {
            "name": "base_unit",
            "label": "Unit",
            "value": resolved["base_unit"],
            "options": [],
        },
        {
            "name": "department",
            "label": "Department",
            "value": resolved["department"],
            "options": department_options,
        },
    ]
