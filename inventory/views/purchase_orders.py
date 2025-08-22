import logging
from typing import Any

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import (
    PurchaseOrderForm,
    PurchaseOrderItemFormSet,
    GRNForm,
)
from ..models import PurchaseOrder, Supplier
from ..services import purchase_order_service, goods_receiving_service

logger = logging.getLogger(__name__)

PO_STATUS_BADGES = {
    "DRAFT": "bg-gray-200 text-gray-800",
    "ORDERED": "bg-blue-200 text-blue-800",
    "PARTIAL": "bg-yellow-200 text-yellow-800",
    "COMPLETE": "bg-green-200 text-green-800",
    "CANCELLED": "bg-red-200 text-red-800",
}


def purchase_orders_list(request):
    orders = PurchaseOrder.objects.select_related("supplier").order_by("-order_date")

    status = request.GET.get("status")
    supplier_id = request.GET.get("supplier")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if status:
        orders = orders.filter(status=status)
    if supplier_id:
        orders = orders.filter(supplier_id=supplier_id)
    if start_date:
        orders = orders.filter(order_date__gte=start_date)
    if end_date:
        orders = orders.filter(order_date__lte=end_date)

    paginator = Paginator(orders, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    for o in page_obj:
        o.badge_class = PO_STATUS_BADGES.get(o.status, "")

    statuses = PurchaseOrder._meta.get_field("status").choices
    suppliers = Supplier.objects.all()

    query_params = request.GET.copy()
    if "page" in query_params:
        query_params.pop("page")
    querystring = query_params.urlencode()

    return render(
        request,
        "inventory/purchase_orders/list.html",
        {
            "orders": page_obj,
            "page_obj": page_obj,
            "statuses": statuses,
            "suppliers": suppliers,
            "current_status": status,
            "current_supplier": supplier_id,
            "start_date": start_date,
            "end_date": end_date,
            "querystring": querystring,
        },
    )


def purchase_order_create(request):
    if request.method == "POST":
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST)
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
        form = PurchaseOrderForm()
        formset = PurchaseOrderItemFormSet()
    return render(
        request,
        "inventory/purchase_orders/form.html",
        {"form": form, "formset": formset, "is_edit": False},
    )


def purchase_order_edit(request, pk: int):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == "POST":
        form = PurchaseOrderForm(request.POST, instance=po)
        formset = PurchaseOrderItemFormSet(request.POST, instance=po)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect("purchase_order_detail", pk=pk)
    else:
        form = PurchaseOrderForm(instance=po)
        formset = PurchaseOrderItemFormSet(instance=po)
    return render(
        request,
        "inventory/purchase_orders/form.html",
        {"form": form, "formset": formset, "is_edit": True, "po": po},
    )


def purchase_order_detail(request, pk: int):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    items = po.purchaseorderitem_set.select_related("item").all()
    badge_class = PO_STATUS_BADGES.get(po.status, "")
    return render(
        request,
        "inventory/purchase_orders/detail.html",
        {"po": po, "items": items, "badge_class": badge_class},
    )


def purchase_order_receive(request, pk: int):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    items = po.purchaseorderitem_set.select_related("item").all()
    if request.method == "POST":
        form = GRNForm(request.POST)
        if form.is_valid():
            any_received = False
            items_data: list[dict[str, Any]] = []
            for item in items:
                qty_field = f"item_{item.pk}"
                try:
                    qty = float(request.POST.get(qty_field, 0) or 0)
                except ValueError:
                    qty = 0
                if qty < 0:
                    qty = 0
                if qty:
                    any_received = True
                    remaining = item.quantity_ordered - item.quantity_received
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
