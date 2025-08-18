"""Database-backed item service utilities for the Django app.

This module extracts a subset of the legacy Streamlit service functions and
makes them available for the Django codebase. Any Streamlit-specific caching is
replaced with :func:`functools.lru_cache` so that callers can clear caches after
mutating operations.
"""
from __future__ import annotations

import logging
import re
import traceback
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce

from inventory.models import Item, StockTransaction
from inventory.unit_inference import infer_units

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cached lookup helpers
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def get_all_items_with_stock(include_inactive: bool = False) -> List[Dict[str, Any]]:
    """Return all items with their current stock as a list of dictionaries."""

    qs = Item.objects.all()
    if not include_inactive:
        qs = qs.filter(is_active=True)
    qs = qs.annotate(_stock=Coalesce(Sum("stocktransaction__quantity_change"), 0.0))
    data = list(
        qs.values(
            "item_id",
            "name",
            "base_unit",
            "purchase_unit",
            "category",
            "sub_category",
            "permitted_departments",
            "reorder_point",
            "notes",
            "is_active",
            "_stock",
        )
    )
    for row in data:
        row["unit"] = row.get("base_unit")
        row["current_stock"] = row.pop("_stock")
    return data


# expose a ``clear`` method like the legacy cache decorator
get_all_items_with_stock.clear = get_all_items_with_stock.cache_clear  # type: ignore[attr-defined]


@lru_cache(maxsize=None)
def suggest_category_and_units(item_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Guess base unit, purchase unit and category for ``item_name``."""

    if not item_name:
        return None, None, None
    tokens = [t for t in re.split(r"\W+", item_name.lower()) if t]
    if not tokens:
        return None, None, None
    for token in tokens:
        row = (
            Item.objects.filter(name__icontains=token)
            .values("base_unit", "purchase_unit", "category")
            .first()
        )
        if row:
            return row["base_unit"], row["purchase_unit"], row["category"]
    return None, None, None


suggest_category_and_units.clear = (
    suggest_category_and_units.cache_clear
)  # type: ignore[attr-defined]


@lru_cache(maxsize=None)
def get_distinct_departments_from_items() -> List[str]:
    """Return a sorted list of unique department names from active items."""

    qs = (
        Item.objects.filter(is_active=True)
        .exclude(permitted_departments__isnull=True)
        .exclude(permitted_departments__exact="")
        .exclude(permitted_departments__exact=" ")
    )
    departments: Set[str] = set()
    for permitted in qs.values_list("permitted_departments", flat=True):
        departments.update({d.strip() for d in permitted.split(",") if d.strip()})
    return sorted(departments)


get_distinct_departments_from_items.clear = (
    get_distinct_departments_from_items.cache_clear
)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Mutating helpers
# ---------------------------------------------------------------------------


@transaction.atomic
def add_new_item(details: Dict[str, Any]) -> Tuple[bool, str]:
    """Insert a single item into the database."""

    s_base, s_purchase, s_category = suggest_category_and_units(details.get("name", ""))
    if s_base and not str(details.get("base_unit", "")).strip():
        details["base_unit"] = s_base
    if s_purchase and not str(details.get("purchase_unit", "")).strip():
        details["purchase_unit"] = s_purchase
    if s_category and not details.get("category"):
        details["category"] = s_category

    if (
        not details.get("base_unit")
        or not str(details.get("base_unit")).strip()
        or not details.get("purchase_unit")
        or not str(details.get("purchase_unit")).strip()
    ):
        inferred_base, inferred_purchase = infer_units(
            details.get("name", ""), details.get("category")
        )
        if not str(details.get("base_unit", "")).strip():
            details["base_unit"] = inferred_base
        if not str(details.get("purchase_unit", "")).strip() and inferred_purchase:
            details["purchase_unit"] = inferred_purchase

    required = ["name", "base_unit"]
    if not all(details.get(k) and str(details.get(k)).strip() for k in required):
        missing = [k for k in required if not details.get(k) or not str(details.get(k)).strip()]
        return False, f"Missing or empty required fields: {', '.join(missing)}"

    notes_val = details.get("notes")
    cleaned_notes = notes_val.strip() if isinstance(notes_val, str) else None
    if cleaned_notes == "":
        cleaned_notes = None

    permitted_val = details.get("permitted_departments")
    cleaned_permitted = (
        permitted_val.strip() if isinstance(permitted_val, str) and permitted_val.strip() else None
    )

    purchase_unit_val = details.get("purchase_unit")
    if isinstance(purchase_unit_val, str):
        purchase_unit_val = purchase_unit_val.strip() or None

    params = dict(
        name=details["name"].strip(),
        base_unit=details["base_unit"].strip(),
        purchase_unit=purchase_unit_val,
        category=(details.get("category", "").strip() or "Uncategorized"),
        sub_category=(details.get("sub_category", "").strip() or "General"),
        permitted_departments=cleaned_permitted,
        reorder_point=details.get("reorder_point", 0.0),
        notes=cleaned_notes,
        is_active=details.get("is_active", True),
    )
    try:
        item = Item.objects.create(**params)
        get_all_items_with_stock.clear()
        get_distinct_departments_from_items.clear()
        return True, f"Item '{item.name}' added with ID {item.pk}."
    except IntegrityError:
        return (
            False,
            f"Item name '{params['name']}' already exists. Choose a unique name.",
        )
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error(
            "ERROR [item_service.add_new_item]: Database error adding item: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred while adding the item."


@transaction.atomic
def add_items_bulk(items: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
    """Insert multiple items in a single transaction."""

    if not items:
        return 0, ["No items provided."]

    processed: List[Dict[str, Any]] = []
    errors: List[str] = []
    for idx, details in enumerate(items):
        s_base, s_purchase, s_category = suggest_category_and_units(
            details.get("name", "")
        )
        if s_base and not str(details.get("base_unit", "")).strip():
            details["base_unit"] = s_base
        if s_purchase and not str(details.get("purchase_unit", "")).strip():
            details["purchase_unit"] = s_purchase
        if s_category and not details.get("category"):
            details["category"] = s_category

        if (
            not details.get("base_unit")
            or not str(details.get("base_unit")).strip()
            or not details.get("purchase_unit")
            or not str(details.get("purchase_unit")).strip()
        ):
            inferred_base, inferred_purchase = infer_units(
                details.get("name", ""), details.get("category")
            )
            if not str(details.get("base_unit", "")).strip():
                details["base_unit"] = inferred_base
            if not str(details.get("purchase_unit", "")).strip() and inferred_purchase:
                details["purchase_unit"] = inferred_purchase

        required = ["name", "base_unit"]
        if not all(details.get(k) and str(details.get(k)).strip() for k in required):
            missing = [k for k in required if not details.get(k) or not str(details.get(k)).strip()]
            errors.append(f"Item {idx} missing required fields: {', '.join(missing)}")
            continue

        notes_val = details.get("notes")
        cleaned_notes = notes_val.strip() if isinstance(notes_val, str) else None
        if cleaned_notes == "":
            cleaned_notes = None

        permitted_val = details.get("permitted_departments")
        cleaned_permitted = (
            permitted_val.strip() if isinstance(permitted_val, str) and permitted_val.strip() else None
        )

        purchase_unit_val = details.get("purchase_unit")
        if isinstance(purchase_unit_val, str):
            purchase_unit_val = purchase_unit_val.strip() or None

        processed.append(
            dict(
                name=details["name"].strip(),
                base_unit=details["base_unit"].strip(),
                purchase_unit=purchase_unit_val,
                category=(details.get("category", "").strip() or "Uncategorized"),
                sub_category=(details.get("sub_category", "").strip() or "General"),
                permitted_departments=cleaned_permitted,
                reorder_point=details.get("reorder_point", 0.0),
                notes=cleaned_notes,
                is_active=details.get("is_active", True),
            )
        )

    if errors:
        return 0, errors

    try:
        objs = [Item(**p) for p in processed]
        Item.objects.bulk_create(objs)
        get_all_items_with_stock.clear()
        get_distinct_departments_from_items.clear()
        return len(objs), []
    except IntegrityError as e:
        return 0, [str(e)]
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error(
            "ERROR [item_service.add_items_bulk]: Database error adding items: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return 0, ["A database error occurred while adding items."]


@transaction.atomic
def remove_items_bulk(item_ids: List[int]) -> Tuple[int, List[str]]:
    """Mark multiple items inactive by ID."""

    if not item_ids:
        return 0, ["No item IDs provided."]

    try:
        affected = Item.objects.filter(item_id__in=item_ids).update(is_active=False)
        if affected:
            get_all_items_with_stock.clear()
            get_distinct_departments_from_items.clear()
        return affected, []
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error(
            "ERROR [item_service.remove_items_bulk]: Database error removing items: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return 0, ["A database error occurred while removing items."]


# ---------------------------------------------------------------------------
# Non-cached detail lookup
# ---------------------------------------------------------------------------


def get_item_details(item_id: int) -> Optional[Dict[str, Any]]:
    """Return the details for a single item."""

    row = (
        Item.objects.filter(pk=item_id)
        .annotate(_stock=Coalesce(Sum("stocktransaction__quantity_change"), 0.0))
        .values(
            "item_id",
            "name",
            "base_unit",
            "purchase_unit",
            "category",
            "sub_category",
            "permitted_departments",
            "reorder_point",
            "notes",
            "is_active",
            "_stock",
        )
        .first()
    )
    if row:
        row["unit"] = row.get("base_unit")
        row["current_stock"] = row.pop("_stock")
        return row
    return None
