"""Department management service for inventory items."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from django.db import IntegrityError, transaction
from django.db.models import Count

from inventory.models import Department, Item, ItemDepartment


@lru_cache(maxsize=16)
def get_all_departments() -> List[Dict[str, Any]]:
    """Return all departments as a list of dictionaries."""
    return list(
        Department.objects
        .all()
        .values('department_id', 'name')
        .order_by('name')
    )


def get_departments_for_item(item_id: int) -> List[Dict[str, Any]]:
    """Get all departments associated with an item."""
    try:
        item = Item.objects.get(pk=item_id)
        return list(
            item.departments
            .values('department_id', 'name')
            .order_by('name')
        )
    except Item.DoesNotExist:
        return []


def get_items_for_department(department_id: int) -> List[Dict[str, Any]]:
    """Get all items associated with a department."""
    try:
        department = Department.objects.get(pk=department_id)
        return list(
            department.items
            .values('item_id', 'name', 'is_active')
            .order_by('name')
        )
    except Department.DoesNotExist:
        return []


@transaction.atomic
def add_item_to_department(item_id: int, department_id: int) -> Tuple[bool, str]:
    """Add an item to a department."""
    try:
        item = Item.objects.get(pk=item_id)
        department = Department.objects.get(pk=department_id)
        
        # Check if relationship already exists
        if ItemDepartment.objects.filter(item=item, department=department).exists():
            return False, f"Item '{item.name}' is already in department '{department.name}'"
        
        # Create the relationship
        ItemDepartment.objects.create(item=item, department=department)
        
        # Clear cache
        get_all_departments.cache_clear()
        
        return True, f"Added '{item.name}' to department '{department.name}'"
        
    except Item.DoesNotExist:
        return False, f"Item with ID {item_id} not found"
    except Department.DoesNotExist:
        return False, f"Department with ID {department_id} not found"
    except IntegrityError as e:
        return False, f"Database error: {str(e)}"


@transaction.atomic
def remove_item_from_department(item_id: int, department_id: int) -> Tuple[bool, str]:
    """Remove an item from a department."""
    try:
        item = Item.objects.get(pk=item_id)
        department = Department.objects.get(pk=department_id)
        
        # Check if relationship exists
        relationship = ItemDepartment.objects.filter(item=item, department=department).first()
        if not relationship:
            return False, f"Item '{item.name}' is not in department '{department.name}'"
        
        # Remove the relationship
        relationship.delete()
        
        # Clear cache
        get_all_departments.cache_clear()
        
        return True, f"Removed '{item.name}' from department '{department.name}'"
        
    except Item.DoesNotExist:
        return False, f"Item with ID {item_id} not found"
    except Department.DoesNotExist:
        return False, f"Department with ID {department_id} not found"


@transaction.atomic
def set_item_departments(item_id: int, department_ids: List[int]) -> Tuple[bool, str]:
    """Set the departments for an item, replacing any existing associations."""
    try:
        item = Item.objects.get(pk=item_id)
        
        # Validate all department IDs exist
        departments = Department.objects.filter(department_id__in=department_ids)
        if departments.count() != len(department_ids):
            found_ids = set(departments.values_list('department_id', flat=True))
            invalid_ids = set(department_ids) - found_ids
            return False, f"Invalid department IDs: {list(invalid_ids)}"
        
        # Clear existing relationships
        ItemDepartment.objects.filter(item=item).delete()
        
        # Create new relationships
        for department in departments:
            ItemDepartment.objects.create(item=item, department=department)
        
        # Clear cache
        get_all_departments.cache_clear()
        
        dept_names = ", ".join(departments.values_list('name', flat=True))
        return True, f"Set departments for '{item.name}': {dept_names}"
        
    except Item.DoesNotExist:
        return False, f"Item with ID {item_id} not found"


@transaction.atomic
def create_department(name: str) -> Tuple[bool, str, Optional[int]]:
    """Create a new department."""
    if not name or not name.strip():
        return False, "Department name cannot be empty", None
    
    name = name.strip()
    
    # Check if department already exists
    if Department.objects.filter(name=name).exists():
        return False, f"Department '{name}' already exists", None
    
    try:
        department = Department.objects.create(name=name)
        
        # Clear cache
        get_all_departments.cache_clear()
        
        return True, f"Created department '{name}'", department.department_id
        
    except IntegrityError as e:
        return False, f"Failed to create department: {str(e)}", None


def get_department_stats() -> Dict[str, Any]:
    """Get statistics about departments and their item associations."""
    stats = {}
    
    # Total departments
    stats['total_departments'] = Department.objects.count()
    
    # Departments with items
    stats['departments_with_items'] = (
        Department.objects
        .filter(items__isnull=False)
        .distinct()
        .count()
    )
    
    # Total item-department relationships
    stats['total_relationships'] = ItemDepartment.objects.count()
    
    # Department breakdown
    stats['department_breakdown'] = list(
        Department.objects
        .annotate(item_count=Count('items'))
        .values('name', 'item_count')
        .order_by('-item_count', 'name')
    )
    
    return stats


# Clear cache function
get_all_departments.clear = get_all_departments.cache_clear
