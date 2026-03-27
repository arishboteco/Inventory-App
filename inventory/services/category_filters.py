"""Category and department filter helpers."""

import logging
from typing import Any, Dict, List

from .categories_service import CategoriesService

logger = logging.getLogger(__name__)


def resolve_category_filters(request) -> Dict[str, Any]:
    """Return selected filter values and available options."""
    from ..models import Department, Supplier, Unit

    category = (request.GET.get("category") or "").strip()
    subcategory = (request.GET.get("subcategory") or "").strip()
    department = [v for v in request.GET.getlist("department") if v.strip()]
    base_unit = (request.GET.get("base_unit") or "").strip()
    supplier = (request.GET.get("supplier") or "").strip()

    try:
        categories_map = CategoriesService.get_category_choices_grouped()
    except Exception:  # pragma: no cover - defensive
        logger.debug("CategoriesService unavailable; returning empty lists")
        categories_map = {}

    categories = list(categories_map.keys())
    subcats = categories_map.get(category, [])
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
        # Simple map for JS to update subcategories on category change
        "category_map": {k: [sc[1] for sc in v] for k, v in categories_map.items()},
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
            "value": [
                v
                for v in (
                    resolved["category"].split(",")
                    if isinstance(resolved["category"], str)
                    else (resolved["category"] or [])
                )
                if v
            ],
            "options": category_options,
            "multiple": True,
        },
        {
            "name": "subcategory",
            "label": "Subcategory",
            "value": [
                v
                for v in (
                    resolved["subcategory"].split(",")
                    if isinstance(resolved["subcategory"], str)
                    else (resolved["subcategory"] or [])
                )
                if v
            ],
            "options": subcategory_options,
            "multiple": True,
        },
        {
            "name": "base_unit",
            "label": "Unit",
            "value": [
                v
                for v in (
                    resolved["base_unit"].split(",")
                    if isinstance(resolved["base_unit"], str)
                    else (resolved["base_unit"] or [])
                )
                if v
            ],
            "options": base_unit_options,
            "multiple": True,
        },
        {
            "name": "supplier",
            "label": "Supplier",
            "value": [
                v
                for v in (
                    resolved["supplier"].split(",")
                    if isinstance(resolved["supplier"], str)
                    else (resolved["supplier"] or [])
                )
                if v
            ],
            "options": supplier_options,
            "multiple": True,
        },
        {
            "name": "department",
            "label": "Department",
            "value": [v for v in resolved["department"] if v],
            "options": department_options,
            "multiple": True,
        },
        {
            "name": "stock_status",
            "label": "Stock",
            "value": request.GET.get("stock_status", ""),
            "options": [
                {"value": "", "label": "All Stock"},
                {"value": "out", "label": "Out of Stock"},
                {"value": "low", "label": "Low Stock"},
                {"value": "normal", "label": "In Stock"},
            ],
            "multiple": False,
        },
    ]
