"""Settings view for managing reference data: units, categories, departments."""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from ..models.category import Category
from ..models.departments import Department
from ..models.unit import Unit

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET", "POST"])
def settings_view(request):
    """Unified settings page for reference data management."""

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "add_unit":
            purchase_unit = request.POST.get("purchase_unit", "").strip()
            base_unit = request.POST.get("base_unit", "").strip()
            conversion_factor = request.POST.get("conversion_factor", "1").strip()
            if purchase_unit and base_unit:
                try:
                    Unit.objects.create(
                        purchase_unit=purchase_unit,
                        base_unit=base_unit,
                        conversion_factor=conversion_factor or "1",
                    )
                    messages.success(request, f"Unit '{purchase_unit}' added.")
                except Exception as exc:
                    logger.error("Failed to add unit: %s", exc)
                    messages.error(request, "Failed to add unit.")
            else:
                messages.error(request, "Purchase unit and base unit are required.")

        elif action == "delete_unit":
            unit_id = request.POST.get("unit_id")
            try:
                Unit.objects.filter(unit_id=unit_id).delete()
                messages.success(request, "Unit deleted.")
            except Exception as exc:
                logger.error("Failed to delete unit: %s", exc)
                messages.error(request, "Failed to delete unit.")

        elif action == "add_category":
            category = request.POST.get("category", "").strip()
            sub_category = request.POST.get("sub_category", "").strip()
            if category:
                try:
                    Category.objects.create(
                        category=category,
                        sub_category=sub_category or "",
                    )
                    messages.success(request, f"Category '{category}' added.")
                except Exception as exc:
                    logger.error("Failed to add category: %s", exc)
                    messages.error(request, "Failed to add category.")
            else:
                messages.error(request, "Category name is required.")

        elif action == "delete_category":
            category_id = request.POST.get("category_id")
            try:
                Category.objects.filter(category_id=category_id).delete()
                messages.success(request, "Category deleted.")
            except Exception as exc:
                logger.error("Failed to delete category: %s", exc)
                messages.error(request, "Failed to delete category.")

        elif action == "add_department":
            name = request.POST.get("name", "").strip()
            if name:
                try:
                    Department.objects.get_or_create(name=name)
                    messages.success(request, f"Department '{name}' added.")
                except Exception as exc:
                    logger.error("Failed to add department: %s", exc)
                    messages.error(request, "Failed to add department.")
            else:
                messages.error(request, "Department name is required.")

        elif action == "delete_department":
            department_id = request.POST.get("department_id")
            try:
                Department.objects.filter(department_id=department_id).delete()
                messages.success(request, "Department deleted.")
            except Exception as exc:
                logger.error("Failed to delete department: %s", exc)
                messages.error(request, "Failed to delete department.")

        return redirect("settings")

    units = Unit.objects.all()
    categories = Category.objects.all()
    departments = Department.objects.all()

    ctx = {
        "units": units,
        "categories": categories,
        "departments": departments,
        "list_url": "/",
        "list_title": "Dashboard",
        "current_title": "Settings",
    }
    return render(request, "inventory/settings.html", ctx)
