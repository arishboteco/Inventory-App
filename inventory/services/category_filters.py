import logging
from typing import Any, Dict, List

from .supabase_categories import get_categories as get_supabase_categories

logger = logging.getLogger(__name__)


def resolve_category_filters(request) -> Dict[str, Any]:
    """Return selected category values and available options."""
    category = (request.GET.get("category") or "").strip()
    subcategory = (request.GET.get("subcategory") or "").strip()

    try:
        categories_map = get_supabase_categories()
    except Exception:  # pragma: no cover - defensive
        categories_map = {}
        logger.exception("Failed to load categories")

    categories = [c["name"] for c in categories_map.get(None, [])]
    subcategories: List[str] = []
    if category:
        subcategories = [c["name"] for c in categories_map.get(category, [])]

    return {
        "category": category,
        "subcategory": subcategory,
        "categories": categories,
        "subcategories": subcategories,
        "categories_map": categories_map,
    }


def build_filters(category_ctx: Dict[str, Any], active_value: str | None = None) -> List[dict]:
    """Return filter definitions combining category data and active status."""
    category = category_ctx["category"]
    subcategory = category_ctx["subcategory"]
    categories = category_ctx["categories"]
    subcategories = category_ctx["subcategories"]

    return [
        {
            "name": "active",
            "value": active_value or "",
            "id": "filter-active",
            "options": [
                {"value": "", "label": "All"},
                {"value": "1", "label": "Active"},
                {"value": "0", "label": "Inactive"},
            ],
        },
        {
            "name": "category",
            "value": category,
            "id": "filter-category",
            "options": [{"value": "", "label": "All"}] + [{"value": c} for c in categories],
        },
        {
            "name": "subcategory",
            "value": subcategory,
            "id": "filter-subcategory",
            "options": [{"value": "", "label": "All"}] + [{"value": sc} for sc in subcategories],
        },
    ]
