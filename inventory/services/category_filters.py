"""Category and department filter helpers."""

import logging
from typing import Any, Dict, List

from .categories_service import CategoriesService

logger = logging.getLogger(__name__)


def resolve_category_filters(request) -> Dict[str, Any]:
    """Return selected filter values and available options."""
    from ..models import Department, Supplier, Unit

    def _values_for(name: str) -> List[str]:
        vals: List[str] = []
        for v in request.GET.getlist(name):
            if v is None:
                continue
            parts = [p.strip() for p in str(v).split(",")]
            vals.extend([p for p in parts if p])
        return vals

    category = _values_for("category")
    subcategory = _values_for("subcategory")
    department = _values_for("department")
    base_unit = _values_for("base_unit")
    supplier = _values_for("supplier")

    try:
        categories_map = CategoriesService.get_category_choices_grouped()
    except Exception:  # pragma: no cover - defensive
        logger.debug("CategoriesService unavailable; returning empty lists")
        categories_map = {}

    categories = list(categories_map.keys())
    subcats: List[tuple] = []
    for c in category:
        subcats.extend(categories_map.get(c, []))
    subcategories = [sc[1] for sc in subcats]

    departments = list(
        Department.objects.all().values_list("department_id", "name").order_by("name")
    )

    base_units = list(
        Unit.objects.order_by("base_unit")
        .values_list("base_unit", flat=True)
        .distinct()
    )

    suppliers = list(
        Supplier.objects.filter(is_active=True)
        .order_by("name")
        .values_list("supplier_id", "name")
    )

    return {
        "category": category,
        "subcategory": subcategory,
        "base_unit": base_unit,
        "supplier": supplier,
        "department": department,
        "categories": categories,
        "subcategories": subcategories,
        "base_units": base_units,
        "units": [],
        "suppliers": suppliers,
        "departments": [(str(did), name) for did, name in departments],
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

    base_unit_options = [{"value": "", "label": "All Units"}]
    for u in resolved["base_units"]:
        base_unit_options.append({"value": u, "label": u})

    supplier_options = [{"value": "", "label": "All Suppliers"}]
    for sid, name in resolved.get("suppliers", []):
        supplier_options.append({"value": str(sid), "label": name})

    department_options = [{"value": "", "label": "All Departments"}]
    for val, label in resolved["departments"]:
        department_options.append({"value": val, "label": label})

    return [
        {
            "name": "category",
            "label": "Category",
            "value": ",".join(resolved["category"]),
            "options": category_options,
        },
        {
            "name": "subcategory",
            "label": "Subcategory",
            "value": ",".join(resolved["subcategory"]),
            "options": subcategory_options,
        },
        {
            "name": "base_unit",
            "label": "Unit",
            "value": ",".join(resolved["base_unit"]),
            "options": base_unit_options,
        },
        {
            "name": "supplier",
            "label": "Supplier",
            "value": ",".join(resolved["supplier"]),
            "options": supplier_options,
        },
        {
            "name": "department",
            "label": "Department",
            "value": ",".join(resolved["department"]),
            "options": department_options,
        },
    ]
