import json
import logging
from decimal import Decimal
from typing import Any

from django.contrib import messages
from django.core.cache import cache
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from ..forms.purchase_forms import GRNForm, PurchaseOrderForm, PurchaseOrderItemFormSet
from ..models import Item, PurchaseOrder, Supplier
from ..services import goods_receiving_service, list_utils, purchase_order_service
from ..services import purchase_order_kpis
from ..services.exceptions import PurchaseOrderServiceError

logger = logging.getLogger(__name__)

PO_STATUS_BADGES = {
    "DRAFT": "bg-gray-200 text-gray-800",
    "ORDERED": "bg-blue-200 text-blue-800",
    "PARTIAL": "bg-warning-soft text-warning-dark",
    "COMPLETE": "bg-success-soft text-success-dark",
    "CANCELLED": "bg-red-200 text-red-800",
}

# Statuses where a PO can still receive goods
RECEIVABLE_STATUSES = {"ORDERED", "PARTIAL"}


def _build_item_prices_json() -> str:
    """Return JSON mapping item pk → last_purchase_price for auto-fill in forms."""
    prices = {
        str(item.pk): float(item.last_purchase_price or item.initial_purchase_price or 0)
        for item in Item.objects.filter(is_active=True).only(
            "item_id", "last_purchase_price", "initial_purchase_price"
        )
    }
    return json.dumps(prices)


def _annotate_total_value(qs):
    """Annotate a PurchaseOrder queryset with total_value (sum of qty * price)."""
    return qs.annotate(
        total_value=Sum(
            ExpressionWrapper(
                F("purchaseorderitem__quantity_ordered") * F("purchaseorderitem__unit_price"),
                output_field=DecimalField(),
            )
        )
    )


class PurchaseOrdersListView(TemplateView):
    """Display purchase orders with quick creation form."""

    template_name = "inventory/purchase_orders/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        orders = _annotate_total_value(PurchaseOrder.objects.select_related("supplier"))

        # Enhanced filters with search capability
        filters = {
            "status": "status",
            "supplier": "supplier_id",
            "start_date": "order_date__gte",
            "end_date": "order_date__lte",
        }

        # Expanded sorting options
        allowed_sorts = {
            "order_date",
            "po_id",
            "supplier__name",
            "status",
            "expected_delivery_date",
        }

        # Apply filters, search, and sorting
        orders, params = list_utils.apply_filters_sort(
            self.request,
            orders,
            search_fields=["po_id", "supplier__name", "notes"],  # NEW: Search support
            filter_fields=filters,
            allowed_sorts=allowed_sorts,
            default_sort="order_date",
            default_direction="desc",
        )

        # Adjustable page size
        page_obj, per_page = list_utils.paginate(
            self.request, orders, default_page_size=20
        )

        progress_map = purchase_order_service.get_orders_progress(
            [o.pk for o in page_obj]
        )
        for o in page_obj:
            o.badge_class = PO_STATUS_BADGES.get(o.status, "")
            o.is_receivable = o.status in RECEIVABLE_STATUSES
            prog = progress_map.get(o.pk)
            if prog:
                o.ordered_total = prog["ordered_total"]
                o.received_total = prog["received_total"]
                o.progress_percent = prog["percent"]
            else:
                o.ordered_total = Decimal("0")
                o.received_total = Decimal("0")
                o.progress_percent = 0

        statuses = PurchaseOrder._meta.get_field("status").choices
        suppliers = Supplier.objects.filter(is_active=True).only("supplier_id", "name").order_by("name")
        querystring = list_utils.build_querystring(self.request)
        supplier_url = reverse("supplier_search")
        quick_form = PurchaseOrderForm(
            prefix="quick", supplier_suggest_url=supplier_url
        )

        # Get KPIs with caching
        try:
            kpis = cache.get_or_set(
                "kpi:purchase_orders:summary",
                purchase_order_kpis.get_po_summary_kpis,
                120  # 2 minute cache
            )
        except Exception as e:  # pragma: no cover - defensive
            logger.exception("Failed to load PO KPIs: %s", e)
            kpis = {
                "total_pos": 0,
                "pending_count": 0,
                "completed_count": 0,
                "total_value": Decimal("0"),
                "pending_value": Decimal("0"),
                "overdue_count": 0,
                "avg_lead_time": 0,
            }

        # View mode (table or cards)
        view_mode = self.request.GET.get("view", "table")

        ctx.update(
            {
                "orders": page_obj,
                "page_obj": page_obj,
                "page_size": per_page,  # NEW: Pass page size
                "statuses": statuses,
                "suppliers": suppliers,
                "querystring": querystring,
                "sortable": True,
                "quick_form": quick_form,
                "list_url": reverse("root"),
                "list_title": "Dashboard",
                "current_title": "Orders",
                "kpis": kpis,  # NEW: KPIs data
                "view": view_mode,  # NEW: View mode
                "export_url": reverse("purchase_orders_export"),  # NEW: Export URL
            }
        )
        ctx.update(params)
        ctx["current_status"] = params.get("status")
        ctx["current_supplier"] = params.get("supplier")
        return ctx

    def post(self, request, *args, **kwargs):
        supplier_url = reverse("supplier_search")
        form = PurchaseOrderForm(
            request.POST, prefix="quick", supplier_suggest_url=supplier_url
        )
        if form.is_valid():
            po = form.save()
            messages.success(request, "Purchase order created", extra_tags="toast")
            return redirect("purchase_order_edit", pk=po.pk)

        ctx = self.get_context_data()
        ctx["quick_form"] = form
        return self.render_to_response(ctx)


purchase_orders_list = PurchaseOrdersListView.as_view()


class PurchaseOrdersTableView(TemplateView):
    """Render only the orders table (HTMX partial).

    Template: inventory/purchase_orders/_table.html
    """

    template_name = "inventory/purchase_orders/_table.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        orders = _annotate_total_value(PurchaseOrder.objects.select_related("supplier"))

        filters = {
            "status": "status",
            "supplier": "supplier_id",
            "start_date": "order_date__gte",
            "end_date": "order_date__lte",
        }

        # Expanded sorting options to match list view
        allowed_sorts = {
            "order_date",
            "po_id",
            "supplier__name",
            "status",
            "expected_delivery_date",
        }

        orders, params = list_utils.apply_filters_sort(
            self.request,
            orders,
            search_fields=["po_id", "supplier__name", "notes"],  # NEW: Search support
            filter_fields=filters,
            allowed_sorts=allowed_sorts,
            default_sort="order_date",
            default_direction="desc",
        )

        page_obj, per_page = list_utils.paginate(
            self.request, orders, default_page_size=20
        )

        progress_map = purchase_order_service.get_orders_progress(
            [o.pk for o in page_obj]
        )
        for o in page_obj:
            o.badge_class = PO_STATUS_BADGES.get(o.status, "")
            o.is_receivable = o.status in RECEIVABLE_STATUSES
            prog = progress_map.get(o.pk)
            if prog:
                o.ordered_total = prog["ordered_total"]
                o.received_total = prog["received_total"]
                o.progress_percent = prog["percent"]
            else:
                o.ordered_total = Decimal("0")
                o.received_total = Decimal("0")
                o.progress_percent = 0

        querystring = list_utils.build_querystring(self.request)
        ctx.update(
            {
                "orders": page_obj,
                "page_obj": page_obj,
                "page_size": per_page,
                "querystring": querystring,
                **params,
            }
        )
        return ctx


class PurchaseOrdersExportView(TemplateView):
    """Export the filtered purchase orders as CSV."""

    def get(self, request):
        orders = PurchaseOrder.objects.select_related("supplier")
        filters = {
            "status": "status",
            "supplier": "supplier_id",
            "start_date": "order_date__gte",
            "end_date": "order_date__lte",
        }
        allowed_sorts = {
            "order_date",
            "po_id",
            "supplier__name",
            "status",
            "expected_delivery_date",
        }
        orders, _ = list_utils.apply_filters_sort(
            request,
            orders,
            search_fields=["po_id", "supplier__name", "notes"],
            filter_fields=filters,
            allowed_sorts=allowed_sorts,
            default_sort="order_date",
            default_direction="desc",
        )

        # Annotate with progress for export
        progress_map = purchase_order_service.get_orders_progress(
            [o.pk for o in orders]
        )

        headers = [
            "PO #",
            "Supplier",
            "Order Date",
            "Expected Delivery",
            "Status",
            "Items Ordered",
            "Items Received",
            "Progress %",
        ]

        def row(po):
            prog = progress_map.get(po.pk, {})
            ordered = prog.get("ordered_total", Decimal("0"))
            received = prog.get("received_total", Decimal("0"))
            percent = prog.get("percent", 0)

            return [
                po.po_id,
                po.supplier.name if po.supplier else "",
                po.order_date.strftime("%Y-%m-%d") if po.order_date else "",
                po.expected_delivery_date.strftime("%Y-%m-%d")
                if po.expected_delivery_date
                else "",
                po.get_status_display(),
                float(ordered),
                float(received),
                percent,
            ]

        return list_utils.export_as_csv(orders, headers, row, "purchase_orders.csv")


class PurchaseOrdersCardsView(TemplateView):
    """Render the paginated card grid of purchase orders."""

    template_name = "inventory/purchase_orders/_cards.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        orders = PurchaseOrder.objects.select_related("supplier")

        filters = {
            "status": "status",
            "supplier": "supplier_id",
            "start_date": "order_date__gte",
            "end_date": "order_date__lte",
        }

        allowed_sorts = {
            "order_date",
            "po_id",
            "supplier__name",
            "status",
            "expected_delivery_date",
        }

        orders, params = list_utils.apply_filters_sort(
            self.request,
            orders,
            search_fields=["po_id", "supplier__name", "notes"],
            filter_fields=filters,
            allowed_sorts=allowed_sorts,
            default_sort="order_date",
            default_direction="desc",
        )

        page_obj, per_page = list_utils.paginate(
            self.request, orders, default_page_size=20
        )

        progress_map = purchase_order_service.get_orders_progress(
            [o.pk for o in page_obj]
        )
        for o in page_obj:
            o.badge_class = PO_STATUS_BADGES.get(o.status, "")
            prog = progress_map.get(o.pk)
            if prog:
                o.ordered_total = prog["ordered_total"]
                o.received_total = prog["received_total"]
                o.progress_percent = prog["percent"]
            else:
                o.ordered_total = Decimal("0")
                o.received_total = Decimal("0")
                o.progress_percent = 0

        querystring = list_utils.build_querystring(self.request)
        ctx.update(
            {
                "orders": page_obj,
                "page_obj": page_obj,
                "page_size": per_page,
                "querystring": querystring,
                "container_id": "purchase_orders_cards",
                **params,
            }
        )
        return ctx


class PurchaseOrderQuickCreatePartialView(View):
    """Render a drawer partial for quick PO creation and handle submissions.

    GET renders `inventory/purchase_orders/_quick_form_partial.html` with a minimal
    form (supplier + order_date). POST validates and creates a draft PO, returning
    JSON suitable for `static/js/modal.js` to close the drawer and redirect.
    """

    template_name = "inventory/purchase_orders/_quick_form_partial.html"

    def get(self, request):
        supplier_url = reverse("supplier_search")
        form = PurchaseOrderForm(supplier_suggest_url=supplier_url)
        ctx = {"form": form}
        return render(request, self.template_name, ctx)

    def post(self, request):
        supplier_url = reverse("supplier_search")
        form = PurchaseOrderForm(request.POST, supplier_suggest_url=supplier_url)
        if form.is_valid():
            po = form.save()
            return JsonResponse(
                {
                    "ok": True,
                    "id": po.pk,
                    "message": "Purchase order created",
                    "redirect": reverse("purchase_order_edit", kwargs={"pk": po.pk}),
                }
            )
        return render(request, self.template_name, {"form": form}, status=400)


class PurchaseOrderCreatePartialView(View):
    """Drawer partial for full PO creation with items formset."""

    template_name = "inventory/purchase_orders/_form_partial.html"

    def get(self, request):
        form = PurchaseOrderForm()
        formset = PurchaseOrderItemFormSet(prefix="items")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "is_edit": False,
                "item_prices_json": _build_item_prices_json(),
            },
        )

    def post(self, request):
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST, prefix="items")
        if form.is_valid() and formset.is_valid():
            po_data: dict[str, Any] = {
                "supplier_id": form.cleaned_data["supplier"].pk,
                "order_date": form.cleaned_data["order_date"],
                "expected_delivery_date": form.cleaned_data.get(
                    "expected_delivery_date"
                ),
                "status": form.cleaned_data.get("status"),
                "notes": form.cleaned_data.get("notes"),
            }
            items_data: list[dict[str, Any]] = []
            for item_form in formset.cleaned_data:
                if item_form and not item_form.get("DELETE", False):
                    items_data.append(
                        {
                            "item_id": item_form["item"].pk,
                            "quantity_ordered": item_form["quantity_ordered"],
                            "unit_price": item_form["unit_price"],
                        }
                    )
            try:
                po = purchase_order_service.create_po(po_data, items_data)
                return JsonResponse(
                    {
                        "ok": True,
                        "id": getattr(po, "pk", None),
                        "message": "Purchase order created",
                        "redirect": reverse(
                            "purchase_order_detail", kwargs={"pk": po.pk}
                        ),
                    }
                )
            except PurchaseOrderServiceError as exc:
                return JsonResponse({"ok": False, "message": str(exc)}, status=400)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "is_edit": False,
                "item_prices_json": _build_item_prices_json(),
            },
            status=400,
        )


def purchase_order_create(request):
    if request.method == "POST":
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST, prefix="items")
        if form.is_valid() and formset.is_valid():
            po_data = {
                "supplier_id": form.cleaned_data["supplier"].pk,
                "order_date": form.cleaned_data["order_date"],
                "expected_delivery_date": form.cleaned_data.get(
                    "expected_delivery_date"
                ),
                "status": form.cleaned_data.get("status"),
                "notes": form.cleaned_data.get("notes"),
            }
            items_data: list[dict[str, Any]] = []
            for item_form in formset.cleaned_data:
                if item_form and not item_form.get("DELETE", False):
                    items_data.append(
                        {
                            "item_id": item_form["item"].pk,
                            "quantity_ordered": item_form["quantity_ordered"],
                            "unit_price": item_form["unit_price"],
                        }
                    )
            try:
                purchase_order_service.create_po(po_data, items_data)
                return redirect("purchase_orders_list")
            except PurchaseOrderServiceError as exc:
                messages.error(request, str(exc), extra_tags="toast")
    else:
        form = PurchaseOrderForm()
        formset = PurchaseOrderItemFormSet(prefix="items")
    return render(
        request,
        "inventory/purchase_orders/form.html",
        {
            "form": form,
            "formset": formset,
            "is_edit": False,
            "item_prices_json": _build_item_prices_json(),
        },
    )


def purchase_order_edit(request, pk: int):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == "POST":
        form = PurchaseOrderForm(request.POST, instance=po)
        formset = PurchaseOrderItemFormSet(request.POST, instance=po, prefix="items")
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect("purchase_order_detail", pk=pk)
    else:
        form = PurchaseOrderForm(instance=po)
        formset = PurchaseOrderItemFormSet(instance=po, prefix="items")
    return render(
        request,
        "inventory/purchase_orders/form.html",
        {
            "form": form,
            "formset": formset,
            "is_edit": True,
            "po": po,
            "item_prices_json": _build_item_prices_json(),
        },
    )


class PurchaseOrderEditPartialView(View):
    """Drawer partial for editing a PO with items formset."""

    template_name = "inventory/purchase_orders/_form_partial.html"

    def get(self, request, pk: int):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        form = PurchaseOrderForm(instance=po)
        formset = PurchaseOrderItemFormSet(instance=po, prefix="items")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "is_edit": True,
                "po": po,
                "item_prices_json": _build_item_prices_json(),
            },
        )

    def post(self, request, pk: int):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        form = PurchaseOrderForm(request.POST, instance=po)
        formset = PurchaseOrderItemFormSet(request.POST, instance=po, prefix="items")
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return JsonResponse(
                {
                    "ok": True,
                    "id": po.pk,
                    "message": "Purchase order updated",
                    "redirect": reverse("purchase_order_detail", kwargs={"pk": po.pk}),
                }
            )
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "is_edit": True,
                "po": po,
                "item_prices_json": _build_item_prices_json(),
            },
            status=400,
        )


def purchase_order_detail(request, pk: int):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    items = (
        po.purchaseorderitem_set.select_related("item")
        .prefetch_related(
            "indent_links",
            "indent_links__indent_item",
            "indent_links__indent_item__indent",
        )
        .annotate(_received_total=Sum("grnitem__quantity_received"))
        .all()
    )
    badge_class = PO_STATUS_BADGES.get(po.status, "")
    rows = [
        ("Supplier", po.supplier.name),
        ("Order Date", po.order_date),
        (
            "Status",
            format_html(
                '<span class="px-2 py-1 rounded text-xs {}">{}</span>',
                badge_class,
                po.get_status_display(),
            ),
        ),
    ]
    ctx = {
        "po": po,
        "items": items,
        "badge_class": badge_class,
        "rows": rows,
        "list_url": reverse("purchase_orders_list"),
        "list_title": "Purchase Orders",
        "current_title": f"Purchase Order {po.pk}",
    }
    return render(request, "inventory/purchase_orders/detail.html", ctx)


def purchase_order_receive(request, pk: int):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    items = (
        po.purchaseorderitem_set.select_related("item")
        .annotate(_received_total=Sum("grnitem__quantity_received"))
        .all()
    )
    if request.method == "POST":
        form = GRNForm(request.POST)
        if form.is_valid():
            any_received = False
            items_data: list[dict[str, Any]] = []
            for item in items:
                qty_field = f"item_{item.pk}"
                try:
                    qty = Decimal(request.POST.get(qty_field, 0) or 0)
                except Exception:
                    qty = Decimal("0")
                if qty < 0:
                    qty = Decimal("0")
                if qty:
                    any_received = True
                    remaining = item.quantity_ordered - item.received_total
                    if qty > remaining:
                        form.add_error(
                            None,
                            f"Received quantity for {item.item.name} exceeds remaining",
                        )
                        continue
                    items_data.append(
                        {
                            "item_id": item.item_id,
                            "po_item_id": item.pk,
                            "quantity_ordered_on_po": item.quantity_ordered,
                            "quantity_received": qty,
                            "unit_price_at_receipt": item.unit_price,
                        }
                    )
            if not any_received:
                form.add_error(None, "No quantities received")
            elif not form.errors:
                grn_data = {
                    "po_id": po.pk,
                    "supplier_id": po.supplier_id,
                    "received_date": form.cleaned_data["received_date"],
                    "notes": form.cleaned_data.get("notes"),
                    "received_by_user_id": getattr(request.user, "username", "System"),
                }
                # Include attachment file if uploaded
                if request.FILES.get("attachment"):
                    grn_data["attachment"] = request.FILES["attachment"]
                success, msg, _ = goods_receiving_service.create_grn(
                    grn_data, items_data
                )
                if success:
                    return redirect("purchase_order_detail", pk=pk)
                messages.error(request, msg, extra_tags="toast")
    else:
        form = GRNForm()
    return render(
        request,
        "inventory/purchase_orders/receive.html",
        {"form": form, "po": po, "items": items},
    )


class PurchaseOrderReceivePartialView(View):
    """Drawer partial for receiving goods against a PO.

    GET renders `inventory/purchase_orders/_receive_partial.html` with GRN form
    and the items receive table. POST validates and creates a GRN via the
    goods_receiving_service, returning JSON for modal.js to handle.
    """

    template_name = "inventory/purchase_orders/_receive_partial.html"

    def get(self, request, pk: int):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        items = (
            po.purchaseorderitem_set.select_related("item")
            .annotate(_received_total=Sum("grnitem__quantity_received"))
            .all()
        )
        form = GRNForm()
        ctx = {"form": form, "po": po, "items": items}
        return render(request, self.template_name, ctx)

    def post(self, request, pk: int):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        items = (
            po.purchaseorderitem_set.select_related("item")
            .annotate(_received_total=Sum("grnitem__quantity_received"))
            .all()
        )
        form = GRNForm(request.POST)
        if form.is_valid():
            any_received = False
            items_data: list[dict[str, Any]] = []
            for item in items:
                qty_field = f"item_{item.pk}"
                try:
                    qty = Decimal(request.POST.get(qty_field, 0) or 0)
                except Exception:
                    qty = Decimal("0")
                if qty < 0:
                    qty = Decimal("0")
                if qty:
                    any_received = True
                    remaining = item.quantity_ordered - item.received_total
                    if qty > remaining:
                        form.add_error(
                            None,
                            f"Received quantity for {item.item.name} exceeds remaining",
                        )
                        continue
                    items_data.append(
                        {
                            "item_id": item.item_id,
                            "po_item_id": item.pk,
                            "quantity_ordered_on_po": item.quantity_ordered,
                            "quantity_received": qty,
                            "unit_price_at_receipt": item.unit_price,
                        }
                    )
            if not any_received:
                form.add_error(None, "No quantities received")
            elif not form.errors:
                grn_data = {
                    "po_id": po.pk,
                    "supplier_id": po.supplier_id,
                    "received_date": form.cleaned_data["received_date"],
                    "notes": form.cleaned_data.get("notes"),
                    "received_by_user_id": getattr(request.user, "username", "System"),
                }
                if request.FILES.get("attachment"):
                    grn_data["attachment"] = request.FILES["attachment"]
                success, msg, _ = goods_receiving_service.create_grn(
                    grn_data, items_data
                )
                if success:
                    return JsonResponse(
                        {
                            "ok": True,
                            "message": "Goods received recorded",
                            "redirect": reverse(
                                "purchase_order_detail", kwargs={"pk": po.pk}
                            ),
                        }
                    )
                return JsonResponse({"ok": False, "message": msg}, status=400)

        # If we reach here, show the partial again with errors
        ctx = {"form": form, "po": po, "items": items}
        return render(request, self.template_name, ctx, status=400)


@require_POST
def mark_ordered(request, pk: int):
    """Transition a PO from DRAFT to ORDERED, recording user and timestamp.

    Adds a lightweight audit note to `notes` and redirects back to detail view.
    """
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if po.status != "DRAFT":
        messages.info(request, "Only draft purchase orders can be marked as ordered.", extra_tags="toast")
        return redirect("purchase_order_detail", pk=pk)
    po.status = "ORDERED"
    # Append audit marker in notes (simple, non-invasive)
    try:
        username = getattr(request.user, "username", None) or getattr(
            request.user, "email", "user"
        )
    except Exception:
        username = "user"
    ts = timezone.now().strftime("%Y-%m-%d %H:%M")
    suffix = f" | Ordered by {username} at {ts}"
    po.notes = ((po.notes or "").strip() + suffix).strip()
    po.save(update_fields=["status", "notes"])
    messages.success(request, "Purchase order marked as ORDERED.", extra_tags="toast")
    return redirect("purchase_order_detail", pk=pk)
