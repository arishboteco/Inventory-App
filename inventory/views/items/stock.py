import logging

from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views import View

from ...forms.bulk_forms import BulkUploadForm
from ...forms.item_forms import ItemForm
from ...models import Department, Item
from ...services.form_service import get_purchase_unit_choices, get_subcategory_choices

logger = logging.getLogger(__name__)


class ItemCreateHTMXView(View):
    """Create an item via HTMX and return updated options."""

    def post(self, request):
        form = ItemForm(request.POST)
        if form.is_valid():
            form.save()
            items = Item.objects.order_by("name")[:50]
            html = render_to_string("inventory/_item_options.html", {"items": items})
            html += "\n<!-- toast: Item created successfully -->\n"
            return HttpResponse(html)
        resp = HttpResponse("Item name is required")
        resp["HX-Retarget"] = "#item-form"
        return resp


class ItemCreatePartialView(View):
    """Serve a compact create-item form for modal/drawer; save returns JSON."""

    template_name = "inventory/_item_create_partial.html"

    def get(self, request):
        form = ItemForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            return JsonResponse(
                {"ok": True, "id": item.item_id, "message": "Item created"}
            )
        return JsonResponse({"ok": False, "message": form.errors.as_json()}, status=400)


class ItemsBulkUploadView(View):
    """Bulk create items from an uploaded CSV file."""

    template_name = "inventory/bulk_upload.html"

    def get(self, request):
        form = BulkUploadForm()
        ctx = {
            "form": form,
            "inserted": 0,
            "errors": [],
            "title": "Bulk Upload Items",
            "back_url": "items_list",
        }
        if (request.GET.get("partial") or "").lower() in {"1", "true", "yes"}:
            return render(request, "inventory/_bulk_upload_partial.html", ctx)
        return render(request, self.template_name, ctx)


class ItemsBulkUpdateView(View):
    """Perform bulk actions on items: deactivate, assign_dept."""

    def post(self, request):
        try:
            data = request.POST
            action = (data.get("action") or "").lower()
            ids = data.getlist("ids[]") or data.getlist("ids")
            ids = [int(x) for x in ids]
            if not ids:
                return JsonResponse(
                    {"ok": False, "message": "No items selected"}, status=400
                )

            if action == "deactivate":
                updated = Item.objects.filter(pk__in=ids).update(is_active=False)
                return JsonResponse({"ok": True, "updated": updated})

            if action == "assign_dept":
                dept_id = data.get("dept_id")
                if not dept_id:
                    return JsonResponse(
                        {"ok": False, "message": "dept_id required"}, status=400
                    )
                try:
                    dept = Department.objects.get(pk=int(dept_id))
                except Department.DoesNotExist:
                    return JsonResponse(
                        {"ok": False, "message": "Department not found"}, status=404
                    )
                items = Item.objects.filter(pk__in=ids)
                for it in items:
                    it.departments.add(dept)
                return JsonResponse({"ok": True, "updated": items.count()})

            if action == "delete":
                deleted_count, _ = Item.objects.filter(pk__in=ids).delete()
                return JsonResponse({"ok": True, "deleted": deleted_count})

            return JsonResponse({"ok": False, "message": "Unknown action"}, status=400)
        except Exception as e:  # pragma: no cover - defensive
            logger.exception("Bulk update failed: %s", e)
            return JsonResponse({"ok": False, "message": "Server error"}, status=500)


class PurchaseUnitsView(View):
    """AJAX endpoint to get purchase units for a given base unit."""

    def get(self, request):
        base_unit = request.GET.get("base_unit", "")
        if base_unit:
            purchase_units = get_purchase_unit_choices(base_unit)
        else:
            purchase_units = []
        return JsonResponse({"purchase_units": purchase_units})


class SubcategoriesView(View):
    """AJAX endpoint to get subcategories for a given category."""

    def get(self, request):
        category = request.GET.get("category", "")
        if category:
            subcategories = get_subcategory_choices(category)
        else:
            subcategories = get_subcategory_choices()
        return JsonResponse({"subcategories": subcategories})


class CheckSimilarNamesView(View):
    """AJAX endpoint to check for similar item names."""

    def get(self, request):
        name = request.GET.get("name", "").strip()
        if not name or len(name) < 3:
            return JsonResponse({"similar_items": [], "has_similar": False})
        similar_items = (
            Item.objects.filter(Q(name__icontains=name) | Q(name__istartswith=name))
            .exclude(name__iexact=name)
            .values("item_id", "name")[:5]
        )
        return JsonResponse(
            {
                "similar_items": list(similar_items),
                "has_similar": len(similar_items) > 0,
            }
        )
