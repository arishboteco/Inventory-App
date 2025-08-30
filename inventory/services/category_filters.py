import logging
from typing import Any, Dict, List, Tuple

from .categories_service import CategoriesService

logger = logging.getLogger(__name__)


def resolve_category_filters(request) -> Dict[str, Any]:
    """Return selected category values and available options.

    Priority: CategoriesService (mockable in tests). Fallback to DB.
    Output format expected by views/tests: lists of strings for
    'categories' and 'subcategories'.
    """
    from ..models import Department, Item

    category = (request.GET.get("category") or "").strip()
    subcategory = (request.GET.get("subcategory") or "").strip()
    base_unit = (request.GET.get("base_unit") or "").strip()
    department = (request.GET.get("department") or "").strip()

    # First try ORM-provided categories (used by tests via monkeypatch)
    categories_map: Dict[str, List[Tuple[int, str]]] = {}
    try:
        categories_map = CategoriesService.get_category_choices_grouped()
    except Exception:  # pragma: no cover - defensive
        logger.debug("CategoriesService unavailable; falling back to DB")

    if categories_map:
        categories = list(categories_map.keys())
        subcats = categories_map.get(category, [])
        subcategories = [sc[1] for sc in subcats]
    else:
        # DB fallback
        categories = list(
            Item.objects.exclude(category__isnull=True)
            .exclude(category="")
            .values_list("category", flat=True)
            .distinct()
            .order_by("category")
        )
        sub_qs = Item.objects.exclude(sub_category__isnull=True).exclude(
            sub_category=""
        )
        if category:
            sub_qs = sub_qs.filter(category=category)
        subcategories = list(
            sub_qs.values_list("sub_category", flat=True)
            .distinct()
            .order_by("sub_category")
        )

    # Base units and departments from DB
    base_units = list(
        Item.objects.exclude(base_unit__isnull=True)
        .exclude(base_unit="")
        .values_list("base_unit", flat=True)
        .distinct()
        .order_by("base_unit")
    )
    departments = list(
        Department.objects.all().values_list("name", flat=True).order_by("name")
    )

    return {
        "category": category,
        "subcategory": subcategory,
        "base_unit": base_unit,
        "department": department,
        "categories": categories,
        "subcategories": subcategories,
        "base_units": [(u, u) for u in base_units],
        "units": [(u, u) for u in base_units],  # Template expects 'units'
        "departments": [(d, d) for d in departments],
    }


def build_filters(request) -> List[Dict[str, Any]]:
    """Build filter UI elements based on request parameters."""
    resolved = resolve_category_filters(request)

    category_options = [{"value": "", "label": "All Categories"}]
    # Categories may be strings or tuples; normalize
    for c in resolved["categories"]:
        if isinstance(c, (list, tuple)) and len(c) >= 1:
            val = c[0]
            lbl = c[1] if len(c) > 1 else c[0]
        else:
            val = lbl = c
        category_options.append({"value": val, "label": lbl})

    subcategory_options = [{"value": "", "label": "All Subcategories"}]
    for c in resolved["subcategories"]:
        if isinstance(c, (list, tuple)) and len(c) >= 1:
            val = c[0]
            lbl = c[1] if len(c) > 1 else c[0]
        else:
            val = lbl = c
        subcategory_options.append({"value": val, "label": lbl})

    base_unit_options = [{"value": "", "label": "All Units"}]
    base_unit_options.extend(
        [{"value": u[0], "label": u[1]} for u in resolved["base_units"]]
    )

    department_options = [{"value": "", "label": "All Departments"}]
    department_options.extend(
        [{"value": d[0], "label": d[1]} for d in resolved["departments"]]
    )

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
