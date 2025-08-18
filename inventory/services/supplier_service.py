import logging
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from django.db import IntegrityError, transaction

from inventory.models import Supplier

logger = logging.getLogger(__name__)


@transaction.atomic
def add_supplier(details: Dict[str, Any]) -> Tuple[bool, str]:
    name = (details.get("name") or "").strip()
    if not name:
        return False, "Supplier name is required and cannot be empty."
    try:
        supplier = Supplier.objects.create(
            name=name,
            contact_person=(details.get("contact_person") or "").strip() or None,
            phone=(details.get("phone") or "").strip() or None,
            email=(details.get("email") or "").strip() or None,
            address=(details.get("address") or "").strip() or None,
            notes=(details.get("notes") or "").strip() or None,
            is_active=details.get("is_active", True),
        )
        return (
            True,
            f"Supplier '{supplier.name}' added successfully with ID {supplier.pk}.",
        )
    except IntegrityError:
        return (
            False,
            f"Supplier name '{name}' already exists. Please use a unique name.",
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error adding supplier: %s", exc)
        return False, "A database error occurred while adding the supplier."


def get_all_suppliers(include_inactive: bool = False):
    qs = Supplier.objects.all()
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return qs


def get_supplier_details(supplier_id: int) -> Optional[Dict[str, Any]]:
    return Supplier.objects.filter(pk=supplier_id).values(
        "supplier_id",
        "name",
        "contact_person",
        "phone",
        "email",
        "address",
        "notes",
        "is_active",
    ).first()


def update_supplier(supplier_id: int, updates: Dict[str, Any]) -> Tuple[bool, str]:
    if not updates:
        return False, "No valid fields provided for update."
    try:
        supplier = Supplier.objects.get(pk=supplier_id)
    except Supplier.DoesNotExist:
        return False, f"Update failed: Supplier ID {supplier_id} not found."
    for field in [
        "name",
        "contact_person",
        "phone",
        "email",
        "address",
        "notes",
    ]:
        if field in updates:
            val = updates[field]
            if isinstance(val, str):
                val = val.strip() or None
            setattr(supplier, field, val)
    try:
        supplier.save()
        return True, f"Supplier ID {supplier_id} updated successfully."
    except IntegrityError:
        return False, f"Update failed: Potential duplicate name '{updates.get('name')}'."
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error updating supplier %s: %s", supplier_id, exc)
        return False, "A database error occurred while updating the supplier."


def deactivate_supplier(supplier_id: int) -> Tuple[bool, str]:
    count = Supplier.objects.filter(pk=supplier_id).update(is_active=False)
    if count:
        return True, "Supplier deactivated successfully."
    return False, "Supplier not found or already inactive."


def reactivate_supplier(supplier_id: int) -> Tuple[bool, str]:
    count = Supplier.objects.filter(pk=supplier_id).update(is_active=True)
    if count:
        return True, "Supplier reactivated successfully."
    return False, "Supplier not found or already active."
