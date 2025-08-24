import logging
from typing import Any

from django.contrib import messages
from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.db.models import Sum

from ..forms.purchase_forms import (
    PurchaseOrderForm,
    PurchaseOrderItemFormSet,
    GRNForm,
)
from ..models import PurchaseOrder, Supplier
from ..services import purchase_order_service, goods_receiving_service, list_utils

logger = logging.getLogger(__name__)

PO_STATUS_BADGES = {
    "DRAFT": "bg-gray-200 text-gray-800",
    "ORDERED": "bg-blue-200 text-blue-800",
    "PARTIAL": "bg-yellow-200 text-yellow-800",
    "COMPLETE": "bg-green-200 text-green-800",
    "CANCELLED": "bg-red-200 text-red-800",
}


def purchase_orders_list(request):
    orders = PurchaseOrder.objects.select_related("supplier")
    filters = {
        "status": "status",
        "supplier": "supplier_id",
        "start_date": "order_date__gte",
        "end_date": "order_date__lte",
    }
    allowed_sorts = {"order_date"}
    orders, params = list_utils.apply_filters_sort(
        request,
        orders,
        filter_fields=filters,
        allowed_sorts=allowed_sorts,
        default_sort="order_date",
        default_direction="desc",
    )
    page_obj, _ = list_utils.paginate(request, orders, default_page_size=20)
    for o in page_obj:
        o.badge_class = PO_STATUS_BADGES.get(o.status, "")
    statuses = PurchaseOrder._meta.get_field("status").choices
    suppliers = Supplier.objects.all()
    querystring = list_utils.build_querystring(request)
    ctx = {
        "orders": page_obj,
        "page_obj": page_obj,
        "statuses": statuses,
        "suppliers": suppliers,
        "querystring": querystring,
        "sortable": True,
    }
    ctx.update(params)
    ctx["current_status"] = params.get("status")
    ctx["current_supplier"] = params.get("supplier")
    return render(request, "inventory/purchase_orders/list.html", ctx)


def purchase_order_create(request):
    item_url = reverse("item_search")
    supplier_url = reverse("supplier_search")
    if request.method == "POST":
        form = PurchaseOrderForm(request.POST, supplier_suggest_url=supplier_url)
        formset = PurchaseOrderItemFormSet(
            request.POST, prefix="items", form_kwargs={"item_suggest_url": item_url}
        )
        if form.is_valid() and formset.is_valid():
            po_data = {
                "supplier_id": form.cleaned_data["supplier"].pk,
                "order_date": form.cleaned_data["order_date"],
                "expected_delivery_date": form.cleaned_data.get("expected_delivery_date"),
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
            success, msg, _ = purchase_order_service.create_po(po_data, items_data)
            if success:
                return redirect("purchase_orders_list")
            messages.error(request, msg)
    else:
        form = PurchaseOrderForm(supplier_suggest_url=supplier_url)
        formset = PurchaseOrderItemFormSet(
            prefix="items", form_kwargs={"item_suggest_url": item_url}
        )
    return render(
        request,
        "inventory/purchase_orders/form.html",
        {"form": form, "formset": formset, "is_edit": False},
    )


def purchase_order_edit(request, pk: int):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    item_url = reverse("item_search")
    supplier_url = reverse("supplier_search")
    if request.method == "POST":
        form = PurchaseOrderForm(
            request.POST, instance=po, supplier_suggest_url=supplier_url
        )
        formset = PurchaseOrderItemFormSet(
            request.POST,
            instance=po,
            prefix="items",
            form_kwargs={"item_suggest_url": item_url},
        )
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect("purchase_order_detail", pk=pk)
    else:
        form = PurchaseOrderForm(instance=po, supplier_suggest_url=supplier_url)
        formset = PurchaseOrderItemFormSet(
            instance=po, prefix="items", form_kwargs={"item_suggest_url": item_url}
        )
    return render(
        request,
        "inventory/purchase_orders/form.html",
        {"form": form, "formset": formset, "is_edit": True, "po": po},
    )


def purchase_order_detail(request, pk: int):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    items = (
        po.purchaseorderitem_set.select_related("item")
        .annotate(_received_total=Sum("grnitem__quantity_received"))
        .all()
    )
    badge_class = PO_STATUS_BADGES.get(po.status, "")
    return render(
        request,
        "inventory/purchase_orders/detail.html",
        {"po": po, "items": items, "badge_class": badge_class},
    )


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
                success, msg, _ = goods_receiving_service.create_grn(grn_data, items_data)
                if success:
                    return redirect("purchase_order_detail", pk=pk)
                messages.error(request, msg)
    else:
        form = GRNForm()
    return render(
        request,
        "inventory/purchase_orders/receive.html",
        {"form": form, "po": po, "items": items},
    )
