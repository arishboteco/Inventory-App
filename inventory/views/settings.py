"""Settings view for managing reference data: units, categories, departments."""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from ..models.category import Category
from ..models.departments import Department, ItemDepartment
from ..models.items import Item
from ..models.unit import Unit

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET", "POST"])
def settings_view(request):
    """Unified settings page for reference data management."""

    if request.method == "POST":
        action = request.POST.get("action", "")

        # ── Units ────────────────────────────────────────────────────────────
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

        elif action == "edit_unit":
            unit_id = request.POST.get("unit_id")
            purchase_unit = request.POST.get("purchase_unit", "").strip()
            base_unit = request.POST.get("base_unit", "").strip()
            conversion_factor = request.POST.get("conversion_factor", "1").strip()
            if purchase_unit and base_unit:
                try:
                    Unit.objects.filter(unit_id=unit_id).update(
                        purchase_unit=purchase_unit,
                        base_unit=base_unit,
                        conversion_factor=conversion_factor or "1",
                    )
                    messages.success(request, f"Unit '{purchase_unit}' updated.")
                except Exception as exc:
                    logger.error("Failed to edit unit: %s", exc)
                    messages.error(request, "Failed to update unit.")
            else:
                messages.error(request, "Purchase unit and base unit are required.")

        elif action == "delete_unit":
            unit_id = request.POST.get("unit_id")
            unit = get_object_or_404(Unit, unit_id=unit_id)
            referencing = Item.objects.filter(unit=unit).count()
            if referencing > 0:
                messages.error(
                    request,
                    f"Cannot delete '{unit.purchase_unit}': {referencing} item(s) use this unit.",
                )
            else:
                try:
                    unit.delete()
                    messages.success(request, "Unit deleted.")
                except Exception as exc:
                    logger.error("Failed to delete unit: %s", exc)
                    messages.error(request, "Failed to delete unit.")

        # ── Categories ───────────────────────────────────────────────────────
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

        elif action == "edit_category":
            category_id = request.POST.get("category_id")
            category_name = request.POST.get("category", "").strip()
            sub_category = request.POST.get("sub_category", "").strip()
            if category_name:
                try:
                    Category.objects.filter(category_id=category_id).update(
                        category=category_name,
                        sub_category=sub_category or "",
                    )
                    messages.success(request, f"Category '{category_name}' updated.")
                except Exception as exc:
                    logger.error("Failed to edit category: %s", exc)
                    messages.error(request, "Failed to update category.")
            else:
                messages.error(request, "Category name is required.")

        elif action == "delete_category":
            category_id = request.POST.get("category_id")
            cat = get_object_or_404(Category, category_id=category_id)
            referencing = Item.objects.filter(category=cat).count()
            if referencing > 0:
                messages.error(
                    request,
                    f"Cannot delete '{cat.category}': {referencing} item(s) use this category.",
                )
            else:
                try:
                    cat.delete()
                    messages.success(request, "Category deleted.")
                except Exception as exc:
                    logger.error("Failed to delete category: %s", exc)
                    messages.error(request, "Failed to delete category.")

        # ── Departments ──────────────────────────────────────────────────────
        elif action == "add_department":
            name = request.POST.get("name", "").strip()
            if name:
                existing = Department.objects.filter(name__iexact=name).first()
                if existing:
                    messages.warning(
                        request,
                        f"A department with a similar name already exists: '{existing.name}'.",
                    )
                else:
                    try:
                        Department.objects.create(name=name)
                        messages.success(request, f"Department '{name}' added.")
                    except Exception as exc:
                        logger.error("Failed to add department: %s", exc)
                        messages.error(request, "Failed to add department.")
            else:
                messages.error(request, "Department name is required.")

        elif action == "edit_department":
            department_id = request.POST.get("department_id")
            name = request.POST.get("name", "").strip()
            if name:
                dup = (
                    Department.objects.filter(name__iexact=name)
                    .exclude(department_id=department_id)
                    .first()
                )
                if dup:
                    messages.warning(
                        request,
                        f"A department with a similar name already exists: '{dup.name}'.",
                    )
                else:
                    try:
                        Department.objects.filter(department_id=department_id).update(
                            name=name
                        )
                        messages.success(request, f"Department '{name}' updated.")
                    except Exception as exc:
                        logger.error("Failed to edit department: %s", exc)
                        messages.error(request, "Failed to update department.")
            else:
                messages.error(request, "Department name is required.")

        elif action == "delete_department":
            department_id = request.POST.get("department_id")
            dept = get_object_or_404(Department, department_id=department_id)
            referencing = ItemDepartment.objects.filter(department=dept).count()
            if referencing > 0:
                messages.error(
                    request,
                    f"Cannot delete '{dept.name}': {referencing} item(s) are assigned to this department.",
                )
            else:
                try:
                    dept.delete()
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


@login_required
@require_http_methods(["GET", "POST"])
def profile_edit_view(request):
    """In-app profile edit — updates first/last name and email."""
    user = request.user
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save(update_fields=["first_name", "last_name", "email"])
        messages.success(request, "Profile updated.", extra_tags="toast")
        return redirect("settings")
    return render(
        request,
        "inventory/user_profile_edit.html",
        {
            "list_url": "/settings/",
            "list_title": "Settings",
            "current_title": "Edit Profile",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def change_password_view(request):
    """In-app change-password form."""
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(
                request, "Password changed successfully.", extra_tags="toast"
            )
            return redirect("settings")
    else:
        form = PasswordChangeForm(request.user)
    return render(
        request,
        "inventory/change_password.html",
        {
            "form": form,
            "list_url": "/settings/",
            "list_title": "Settings",
            "current_title": "Change Password",
        },
    )
