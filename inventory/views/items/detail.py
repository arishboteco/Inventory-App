import json
import logging
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from ...forms.item_forms import ItemForm
from ...models import Item, StockTransaction
from ...services import item_service, stock_service
from .constants import EXCLUDED_FIELDS
from .list import ItemsTableView

logger = logging.getLogger(__name__)


class ItemEditView(View):
    """Edit an existing item."""

    template_name = "inventory/item_form.html"

    def get_object(self, pk: int):
        try:
            return get_object_or_404(Item, pk=pk)
        except (DatabaseError, ValueError):  # pragma: no cover - defensive
            logger.exception("Error retrieving item %s", pk)
            raise Http404("Item not found")

    def get(self, request, pk: int):
        item = self.get_object(pk)
        try:
            form = ItemForm(instance=item)
        except (DatabaseError, ValueError):
            logger.exception("Error loading form for item %s", pk)
            messages.error(request, "Unable to load item")
            return redirect("items_list")
        ctx = {
            "form": form,
            "is_edit": True,
            "item": item,
            "excluded_fields": EXCLUDED_FIELDS,
            "list_url": reverse("items_list"),
            "list_title": "Items",
            "current_title": item.name,
        }
        if (request.GET.get("partial") or "").lower() in {"1", "true", "yes"}:
            return render(request, "inventory/_item_form_partial.html", ctx)
        return render(request, self.template_name, ctx)

    def post(self, request, pk: int):
        item = self.get_object(pk)
        try:
            form = ItemForm(request.POST, instance=item)
        except (DatabaseError, ValueError):
            logger.exception("Error loading form for item %s", pk)
            messages.error(request, "Unable to load item")
            return redirect("items_list")
        if form.is_valid():
            try:
                form.save()
                item_service.get_all_items_with_stock.clear()
                item_service.get_distinct_departments_from_items.clear()
                if (request.POST.get("partial") or "").lower() in {"1", "true", "yes"}:
                    return JsonResponse({"ok": True, "message": "Item updated"})
                messages.success(request, "Item updated")
                return redirect("items_list")
            except (ValidationError, DatabaseError):
                if (request.POST.get("partial") or "").lower() in {"1", "true", "yes"}:
                    return JsonResponse(
                        {"ok": False, "message": "Unable to save item"}, status=400
                    )
                messages.error(request, "Unable to save item")
        ctx = {
            "form": form,
            "is_edit": True,
            "item": item,
            "excluded_fields": EXCLUDED_FIELDS,
            "list_url": reverse("items_list"),
            "list_title": "Items",
            "current_title": item.name,
        }
        if (request.POST.get("partial") or "").lower() in {"1", "true", "yes"}:
            return render(request, "inventory/_item_form_partial.html", ctx, status=400)
        return render(request, self.template_name, ctx)


class ItemInlineUpdateView(View):
    """Minimal inline update endpoint for quick edits in the items table."""

    def post(self, request, pk: int):
        item = get_object_or_404(Item, pk=pk)
        data = request.POST

        editable_fields = {
            "name",
            "item_code",
            "category",
            "sub_category",
            "base_unit",
            "current_stock",
            "reorder_point",
            "notes",
            "is_active",
        }
        changed = False
        for field in editable_fields:
            if field in data:
                val = data.get(field)
                if field == "is_active":
                    val = val in ("1", "true", "on", "True")
                if field == "reorder_point":
                    try:
                        val = Decimal(str(val)) if val not in (None, "") else None
                    except Exception:
                        continue
                if field == "current_stock":
                    try:
                        val = Decimal(str(val)) if val not in (None, "") else None
                    except Exception:
                        continue
                setattr(item, field, val)
                changed = True

        if "unit" in data:
            try:
                uid = int(data.get("unit")) if data.get("unit") else None
            except (TypeError, ValueError):
                uid = None
            if uid:
                item.unit_id = uid
                changed = True

        if "category" in data:
            try:
                cid = int(data.get("category")) if data.get("category") else None
            except (TypeError, ValueError):
                cid = None
            if cid:
                item.category_id = cid
                changed = True

        if changed:
            try:
                item.save()
                item_service.get_all_items_with_stock.clear()
                item_service.get_distinct_departments_from_items.clear()
                return JsonResponse({"ok": True, "message": "Item updated"})
            except Exception as e:  # pragma: no cover - defensive
                logger.exception("Inline update failed for item %s: %s", pk, e)
                return JsonResponse({"ok": False, "message": "Save failed"}, status=400)
        return JsonResponse({"ok": True, "message": "No changes"})


class ItemDetailView(View):
    """Display item details with stock history."""

    template_name = "inventory/item_detail.html"

    def get(self, request, pk: int):
        try:
            details = item_service.get_item_details(pk)
        except (DatabaseError, ValueError):  # pragma: no cover - defensive
            logger.exception("Error retrieving item %s", pk)
            raise Http404("Item not found")
        if not details:
            raise Http404("Item not found")

        rows = [
            ("ID", details["item_id"]),
            ("Name", details["name"]),
            ("Category", details.get("category", "Not set")),
            ("Sub Category", details.get("sub_category", "Not set")),
            ("Base Unit", details.get("base_unit", "Not set")),
            ("Purchase Unit", details.get("purchase_unit", "Not set")),
            ("Departments", details.get("department_names", "None")),
            ("Current Stock", details["current_stock"]),
            ("Reorder Point", details["reorder_point"]),
            (
                "Initial Purchase Price",
                details.get("initial_purchase_price", "Not set"),
            ),
            ("Minimum Order Qty", details.get("minimum_order_qty", "Not set")),
            ("Lead Time (Days)", details.get("lead_time_days", "Not set")),
            ("Notes", details.get("notes", "None")),
            ("Active", "Yes" if details["is_active"] else "No"),
        ]
        recent_activity = StockTransaction.objects.filter(item_id=pk).order_by(
            "-transaction_date"
        )[:5]
        stock_history = stock_service.get_stock_history(pk)
        ctx = {
            "item": details,
            "rows": rows,
            "recent_activity": recent_activity,
            "stock_history": json.dumps(stock_history),
            "list_url": reverse("items_list"),
            "list_title": "Items",
            "current_title": details["name"],
        }
        if (request.GET.get("partial") or "").lower() in {"1", "true", "yes"}:
            return render(request, "inventory/_item_detail_partial.html", ctx)
        return render(request, self.template_name, ctx)


class ItemDeleteView(View):
    """Confirm and process deletion or deactivation of an item."""

    template_name = "inventory/item_confirm_delete.html"

    def get_object(self, pk: int):
        try:
            return get_object_or_404(Item, pk=pk)
        except (DatabaseError, ValueError):  # pragma: no cover - defensive
            logger.exception("Error retrieving item %s", pk)
            raise Http404("Item not found")

    def get(self, request, pk: int):
        item = self.get_object(pk)
        return render(request, self.template_name, {"item": item})

    def post(self, request, pk: int):
        item = self.get_object(pk)
        is_fetch = request.headers.get("x-requested-with") == "fetch"
        if StockTransaction.objects.filter(item=item).exists():
            ok, _ = item_service.deactivate_item(item.pk)
            if is_fetch:
                return JsonResponse({"ok": ok})
            if ok:
                messages.success(request, "Item deactivated")
            else:  # pragma: no cover - defensive
                messages.error(request, "Unable to delete item")
            return redirect("items_list")
        try:
            item.delete()
            item_service.get_all_items_with_stock.clear()
            item_service.get_distinct_departments_from_items.clear()
            if is_fetch:
                return JsonResponse({"ok": True})
            messages.success(request, "Item deleted")
        except IntegrityError:
            ok, _ = item_service.deactivate_item(item.pk)
            if is_fetch:
                return JsonResponse({"ok": ok})
            if ok:
                messages.success(request, "Item deactivated")
            else:  # pragma: no cover - defensive
                messages.error(request, "Unable to delete item")
        except DatabaseError:  # pragma: no cover - defensive
            logger.exception("Error deleting item %s", pk)
            if is_fetch:
                return JsonResponse({"ok": False}, status=400)
            messages.error(request, "Unable to delete item")
        return redirect("items_list")


@method_decorator(csrf_protect, name="dispatch")
class ItemToggleActiveView(View):
    """Toggle an item's active flag and return updated table."""

    def _toggle(self, request, pk: int):
        item = get_object_or_404(Item, pk=pk)
        if item.is_active:
            item_service.deactivate_item(item.pk)
        else:
            item_service.reactivate_item(item.pk)
        if request.method == "POST":
            params = request.POST.copy()
            params.pop("csrfmiddlewaretoken", None)
            request.GET = params
            request.method = "GET"
        return ItemsTableView.as_view()(request)

    def post(self, request, pk: int):
        return self._toggle(request, pk)

    def get(self, request, pk: int):
        return self._toggle(request, pk)
