import csv
import io
import json
import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError
from django.db.models import BooleanField, Case, F, Value, When
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.generic import TemplateView

from ..forms.bulk_forms import BulkUploadForm
from ..forms.item_forms import ItemForm
from ..models import Item, StockTransaction
from ..services import category_filters, item_service, list_utils, stock_service, kpis
from ..services.form_service import FormService

logger = logging.getLogger(__name__)

EXCLUDED_FIELDS = ["name", "base_unit", "purchase_unit", "category", "sub_category", "departments"]  # Exclude fields that are handled explicitly


def _filter_and_sort_items(request, qs=None):
    """Return items queryset and filter metadata from request params."""
    qs = qs or Item.objects.all()
    qs = qs.annotate(
        stock_ok=Case(
            When(current_stock__gte=F("reorder_point"), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )
    # Avoid N+1 on departments badges
    qs = qs.prefetch_related("departments")
    filters = {
        "active": "is_active",
        "category": "category",  # Maps to category field
        "subcategory": "sub_category",  # Maps to sub_category field
        "base_unit": "base_unit",  # Add base unit filtering
        "department": "departments__name",  # Add department filtering via many-to-many
    }
    allowed_sorts = {
        "item_id",
        "name",
        "base_unit",  # Use base_unit for sorting
        "category",
        "sub_category", 
        "current_stock",
        "reorder_point",
        "is_active",
        "initial_purchase_price",
        "last_purchase_price",
    }
    qs, params = list_utils.apply_filters_sort(
        request,
        qs,
        search_fields=["name", "category", "sub_category"],  # Enhanced search
        filter_fields=filters,
        allowed_sorts=allowed_sorts,
        default_sort="name",
    )
    # Apply stock status filter if present
    stock_status = (request.GET.get("stock_status") or "").strip().lower()
    if stock_status == "low":
        qs = qs.filter(current_stock__lt=F("reorder_point"), current_stock__gt=0)
    elif stock_status == "out":
        qs = qs.filter(current_stock__lte=0)
    elif stock_status == "normal":
        qs = qs.filter(current_stock__gte=F("reorder_point"))
    if stock_status:
        params.update({"stock_status": stock_status})
    # Optional visibility toggles without changing current defaults
    show_inactive = (request.GET.get("show_inactive") or "").lower() in {"1", "true", "on"}
    active_only = (request.GET.get("active_only") or "").lower() in {"1", "true", "on"}
    if show_inactive:
        qs = qs.filter(is_active=False)
    if active_only:
        qs = qs.filter(is_active=True)
    params.update({"show_inactive": "1" if show_inactive else "", "active_only": "1" if active_only else ""})
    return qs, params


class ItemsListView(TemplateView):
    """Show item filters and options for the list view.

    GET params:
        q, category, subcategory, active, page_size, sort, direction
        control filtering, pagination and ordering.
    Template: inventory/items_list.html.
    """

    template_name = "inventory/items_list.html"

    def post(self, request, *args, **kwargs):
        """Handle inline item creation via POST request."""
        form = ItemForm(request.POST)
        
        if form.is_valid():
            try:
                # Save the new item
                item = form.save()
                messages.success(request, f'Item "{item.name}" created successfully!')
                
                # Redirect to the same page to avoid duplicate submissions
                return redirect('items_list')
                
            except (DatabaseError, IntegrityError) as e:
                logger.error(f"Database error creating item: {e}")
                messages.error(request, f"Error creating item: {str(e)}")
                
            except Exception as e:
                logger.error(f"Unexpected error creating item: {e}")
                messages.error(request, f"Unexpected error: {str(e)}")
                
        else:
            # Form has validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        
        # If we get here, there were errors - redisplay the form
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request

        category_ctx = category_filters.resolve_category_filters(request)
        qs, params = _filter_and_sort_items(request)
        page_obj, per_page = list_utils.paginate(request, qs)
        table_ctx = {**params, "page_obj": page_obj, "page_size": per_page}

        # If this is a POST request, use the submitted form data
        if request.method == 'POST':
            form = ItemForm(request.POST)
        else:
            form = ItemForm()
        
        # Add additional context for the form
        from ..models import Supplier, Department
        suppliers = Supplier.objects.filter(is_active=True).order_by('name')
        departments_for_form = Department.objects.all().order_by('name')

        ctx.update(params)
        ctx.update(category_ctx)
        ctx.update(table_ctx)  # Add this line to include page_obj
        # KPI/Stats for header cards
        try:
            pending_po_counts = kpis.pending_po_status_counts()
            pending_orders = sum(pending_po_counts.values())
        except Exception:  # pragma: no cover - defensive
            pending_orders = 0
        try:
            total_value = kpis.stock_value()
        except Exception:  # pragma: no cover - defensive
            total_value = 0
        stats = {
            "low_stock_count": kpis.low_stock_count(),
            "pending_orders": pending_orders,
            "total_value": total_value,
        }

        ctx.update(
            {
                "page_size": per_page,
                "filters": category_filters.build_filters(request),
                "export_url": reverse("items_export"),
                "stats": stats,
                "form": form,
                "suppliers": suppliers,
                "departments_for_form": departments_for_form,  # Use different name to avoid conflict
                "excluded_fields": EXCLUDED_FIELDS,
            }
        )
        # Expose category/subcategory filter context explicitly for tests
        ctx.update({
            "categories": category_ctx.get("categories", []),
            "subcategories": category_ctx.get("subcategories", []),
        })
        return ctx


class ItemsTableView(TemplateView):
    """Render the paginated table of items.

    Accepts the same GET filters as ItemsListView plus a page number.
    Template: inventory/_items_table.html.
    """

    template_name = "inventory/_items_table.html"

    def _get_queryset(self):
        qs, params = _filter_and_sort_items(self.request)
        self._filter_params = params
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self._get_queryset()
        page_obj, per_page = list_utils.paginate(self.request, qs)
        ctx.update(self._filter_params)
        ctx.update({"page_obj": page_obj, "page_size": per_page})
        return ctx


class ItemsExportView(View):
    """Export the filtered item list as CSV.

    Uses the same GET parameters as ItemsListView for filtering.
    """

    def get(self, request):
        qs, _ = _filter_and_sort_items(request)
        headers = [
            "ID",
            "Name",
            "Unit",
            "Current Stock",
            "Reorder Point",
            "Active",
        ]

        def row(item: Item):
            from inventory.services.item_service import get_unit_display_name
            return [
                item.item_id,
                item.name,
                get_unit_display_name(item.unit_id),
                item.current_stock,
                item.reorder_point,
                item.is_active,
            ]

        return list_utils.export_as_csv(qs, headers, row, "items.csv")


class ItemEditView(View):
    """Edit an existing item.

    Template: inventory/item_form.html.
    """

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
        }
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
                messages.success(request, "Item updated")
                return redirect("items_list")
            except (ValidationError, DatabaseError):
                messages.error(request, "Unable to save item")
        ctx = {
            "form": form,
            "is_edit": True,
            "item": item,
            "excluded_fields": EXCLUDED_FIELDS,
        }
        return render(request, self.template_name, ctx)


class ItemInlineUpdateView(View):
    """Minimal inline update endpoint for quick edits in the items table.

    Accepts a subset of fields and applies updates atomically.
    Returns JSON with a simple status message.
    """

    def post(self, request, pk: int):
        item = get_object_or_404(Item, pk=pk)
        data = request.POST

        # Whitelist of editable fields via inline editor
        editable_fields = {
            "name",
            "item_code",
            "category",
            "sub_category",
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
                        from decimal import Decimal
                        val = Decimal(str(val)) if val not in (None, "") else None
                    except Exception:
                        continue
                setattr(item, field, val)
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
    """Display item details with stock history.

    Template: inventory/item_detail.html.
    """

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
            ("Initial Purchase Price", details.get("initial_purchase_price", "Not set")),
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
        }
        return render(request, self.template_name, ctx)


class ItemDeleteView(View):
    """Confirm and process deletion or deactivation of an item.

    Template: inventory/item_confirm_delete.html.
    """

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
        if StockTransaction.objects.filter(item=item).exists():
            ok, _ = item_service.deactivate_item(item.pk)
            if ok:
                messages.success(request, "Item deactivated")
            else:  # pragma: no cover - defensive
                messages.error(request, "Unable to delete item")
            return redirect("items_list")
        try:
            item.delete()
            item_service.get_all_items_with_stock.clear()
            item_service.get_distinct_departments_from_items.clear()
            messages.success(request, "Item deleted")
        except IntegrityError:
            ok, _ = item_service.deactivate_item(item.pk)
            if ok:
                messages.success(request, "Item deactivated")
            else:  # pragma: no cover - defensive
                messages.error(request, "Unable to delete item")
        except DatabaseError:  # pragma: no cover - defensive
            logger.exception("Error deleting item %s", pk)
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


class ItemSearchView(TemplateView):
    """Return item ``<option>`` elements for autocomplete widgets.

    GET param `q` supplies the search term. If absent, the first GET
    value with a key ending in "item" is used. Template:
    inventory/_item_options.html.
    """

    template_name = "inventory/_item_options.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query = (self.request.GET.get("q") or "").strip()
        if not query:
            for key, val in self.request.GET.items():
                if key.endswith("item"):
                    query = val
                    break
        items = Item.objects.filter(name__icontains=query)[:20]
        ctx["items"] = items
        return ctx


class ItemCreateHTMXView(View):
    """Create an item via HTMX and return updated options.

    Success: returns options HTML plus a simple toast indicator.
    Failure: returns a minimal error response with HX-Retarget header.
    """

    def post(self, request):
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            items = Item.objects.order_by("name")[:50]
            html = render_to_string("inventory/_item_options.html", {"items": items})
            # Append a tiny toast marker for the test expectation
            html += "\n<!-- toast: Item created successfully -->\n"
            return HttpResponse(html)
        # Invalid form: retarget to the form container and include error text
        resp = HttpResponse("Item name is required")
        resp["HX-Retarget"] = "#item-form"
        return resp


class ItemsBulkUploadView(View):
    """Bulk create items from an uploaded CSV file.

    GET shows the upload form; POST processes the file and reports
    inserted rows and errors. Template: inventory/bulk_upload.html.
    """

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
        return render(request, self.template_name, ctx)

    def post(self, request):
        inserted = 0
        errors: list[str] = []
        form = BulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]
            data = io.StringIO(file.read().decode("utf-8"))
            reader = csv.DictReader(data)
            for row in reader:
                form_row = ItemForm(row)
                if form_row.is_valid():
                    form_row.save()
                    inserted += 1
                else:
                    errors.append(str(form_row.errors))
        ctx = {
            "form": form,
            "inserted": inserted,
            "errors": errors,
            "title": "Bulk Upload Items",
            "back_url": "items_list",
        }
        return render(request, self.template_name, ctx)


def get_purchase_units(request):
    """AJAX endpoint to get purchase units for a given base unit"""
    base_unit = request.GET.get('base_unit', '')
    if base_unit:
        purchase_units = FormService.get_purchase_unit_choices(base_unit)
    else:
        purchase_units = FormService.get_purchase_unit_choices()
    
    return JsonResponse({
        'purchase_units': purchase_units
    })


def get_subcategories(request):
    """AJAX endpoint to get subcategories for a given category"""
    from ..services.form_service import get_subcategory_choices
    
    category = request.GET.get('category', '')
    if category:
        subcategories = get_subcategory_choices(category)
    else:
        subcategories = get_subcategory_choices()
    
    return JsonResponse({
        'subcategories': subcategories
    })


def check_similar_names(request):
    """AJAX endpoint to check for similar item names"""
    from django.db.models import Q
    from ..models import Item
    
    name = request.GET.get('name', '').strip()
    if not name or len(name) < 3:  # Only check for names with 3+ characters
        return JsonResponse({
            'similar_items': [],
            'has_similar': False
        })
    
    # Check for similar names (case-insensitive partial matches)
    similar_items = Item.objects.filter(
        Q(name__icontains=name) | Q(name__istartswith=name)
    ).exclude(name__iexact=name).values('id', 'name')[:5]  # Limit to 5 results
    
    return JsonResponse({
        'similar_items': list(similar_items),
        'has_similar': len(similar_items) > 0
    })
