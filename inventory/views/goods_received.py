import csv
import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib import messages
from django.db.models import (
    DecimalField,
    Exists,
    ExpressionWrapper,
    F,
    OuterRef,
    Sum,
)
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import format_html
from django.views import View
from django.views.generic import TemplateView
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from ..forms.purchase_forms import GRNForm
from ..models import GoodsReceivedNote, GRNItem, PurchaseOrder, Supplier
from ..services import goods_receiving_service, list_utils

logger = logging.getLogger(__name__)

# Statuses that allow goods to be received
RECEIVABLE_STATUSES = ["SENT", "RECEIVED"]


def _grn_kpis():
    """Return KPI dict for the GRN list page."""
    today = date.today()
    month_qs = GoodsReceivedNote.objects.filter(
        received_date__year=today.year,
        received_date__month=today.month,
    )
    discrepancy_qs = GoodsReceivedNote.objects.filter(
        Exists(
            GRNItem.objects.filter(
                grn=OuterRef("pk"),
                quantity_received__lt=F("quantity_ordered_on_po"),
            )
        )
    )
    value_this_month = GRNItem.objects.filter(grn__in=month_qs).aggregate(
        total=Sum(
            ExpressionWrapper(
                F("quantity_received") * F("unit_price_at_receipt"),
                output_field=DecimalField(),
            )
        )
    )["total"] or Decimal("0")
    return {
        "total_grns": GoodsReceivedNote.objects.count(),
        "grns_this_month": month_qs.count(),
        "discrepancy_count": discrepancy_qs.count(),
        "value_this_month": value_this_month,
    }


class GRNListView(TemplateView):
    """List goods received notes with filter and sort options."""

    template_name = "inventory/grns/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request
        grns = GoodsReceivedNote.objects.select_related(
            "purchase_order", "supplier"
        ).prefetch_related("grnitem_set__po_item__item")

        # Annotate discrepancy flag
        grns = grns.annotate(
            has_discrepancy=Exists(
                GRNItem.objects.filter(
                    grn=OuterRef("pk"),
                    quantity_received__lt=F("quantity_ordered_on_po"),
                )
            )
        )

        filters = {
            "supplier": "supplier_id",
            "start_date": "received_date__gte",
            "end_date": "received_date__lte",
        }
        allowed_sorts = {"received_date", "grn_id"}
        grns, params = list_utils.apply_filters_sort(
            request,
            grns,
            filter_fields=filters,
            allowed_sorts=allowed_sorts,
            default_sort="received_date",
            default_direction="desc",
        )
        page_obj, _ = list_utils.paginate(request, grns, default_page_size=20)
        suppliers = Supplier.objects.filter(is_active=True).order_by("name")
        open_pos = (
            PurchaseOrder.objects.filter(status__in=RECEIVABLE_STATUSES)
            .select_related("supplier")
            .order_by("-order_date")
        )
        querystring = list_utils.build_querystring(request)
        ctx.update(
            {
                "grns": page_obj,
                "page_obj": page_obj,
                "suppliers": suppliers,
                "open_pos": open_pos,
                "querystring": querystring,
                "kpis": _grn_kpis(),
                "today": date.today().strftime("%Y-%m-%d"),
                "list_url": reverse("root"),
                "list_title": "Dashboard",
                "current_title": "GRNs",
            }
        )
        ctx.update(params)
        ctx["current_supplier"] = params.get("supplier")
        ctx["quick_form"] = kwargs.get("quick_form") or GRNForm()
        return ctx

    def post(self, request, *args, **kwargs):
        form = GRNForm(request.POST)
        if form.is_valid():
            po_id = request.POST.get("po")
            try:
                po = PurchaseOrder.objects.prefetch_related(
                    "purchaseorderitem_set"
                ).get(pk=po_id)
            except PurchaseOrder.DoesNotExist:
                form.add_error(None, "Invalid purchase order")
            else:
                items = po.purchaseorderitem_set.all()
                items_data = [
                    {
                        "item_id": item.item_id,
                        "po_item_id": item.pk,
                        "quantity_ordered_on_po": item.quantity_ordered,
                        "quantity_received": item.quantity_ordered,
                        "unit_price_at_receipt": item.unit_price,
                    }
                    for item in items
                ]
                grn_data = {
                    "po_id": po.pk,
                    "supplier_id": po.supplier_id,
                    "received_date": form.cleaned_data["received_date"],
                    "notes": form.cleaned_data.get("notes"),
                    "received_by_user_id": getattr(request.user, "username", "System"),
                }
                success, msg, grn_id = goods_receiving_service.create_grn(
                    grn_data, items_data
                )
                if success:
                    messages.success(request, "GRN created", extra_tags="toast")
                    return redirect("grn_list")
                messages.error(request, msg, extra_tags="toast")
        ctx = self.get_context_data(quick_form=form)
        return self.render_to_response(ctx)


class GRNCreateView(View):
    """Full GRN creation page: select a PO, then enter received quantities per line item.

    GET /grns/create/           — show PO selector
    GET /grns/create/?po=<pk>   — show item table pre-populated from PO
    POST /grns/create/?po=<pk>  — validate + create GRN, redirect to GRN detail
    """

    template_name = "inventory/grns/create.html"

    def _get_po_and_items(self, po_pk):
        from django.db.models import Sum as _Sum

        po = get_object_or_404(PurchaseOrder, pk=po_pk)
        items = (
            po.purchaseorderitem_set.select_related("item", "item__unit")
            .annotate(received_total_qty=_Sum("grnitem__quantity_received"))
            .all()
        )
        # Only items with remaining quantity
        remaining_items = []
        for item in items:
            received = item.received_total_qty or Decimal("0")
            remaining = item.quantity_ordered - received
            if remaining > 0:
                item.prev_received = received
                item.remaining_qty = remaining
                remaining_items.append(item)
        return po, remaining_items

    def get(self, request):
        po_pk = request.GET.get("po")
        open_pos = (
            PurchaseOrder.objects.filter(status__in=RECEIVABLE_STATUSES)
            .select_related("supplier")
            .order_by("-order_date")
        )

        if not po_pk:
            return render(
                request,
                self.template_name,
                {
                    "step": "select_po",
                    "open_pos": open_pos,
                    "today": date.today().strftime("%Y-%m-%d"),
                },
            )

        po, items = self._get_po_and_items(po_pk)
        form = GRNForm(initial={"received_date": date.today()})
        return render(
            request,
            self.template_name,
            {
                "step": "enter_quantities",
                "po": po,
                "items": items,
                "form": form,
                "open_pos": open_pos,
                "today": date.today().strftime("%Y-%m-%d"),
            },
        )

    def post(self, request):
        po_pk = request.GET.get("po") or request.POST.get("po_id")
        po, items = self._get_po_and_items(po_pk)
        form = GRNForm(request.POST)
        open_pos = (
            PurchaseOrder.objects.filter(status__in=RECEIVABLE_STATUSES)
            .select_related("supplier")
            .order_by("-order_date")
        )

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "step": "enter_quantities",
                    "po": po,
                    "items": items,
                    "form": form,
                    "open_pos": open_pos,
                    "today": date.today().strftime("%Y-%m-%d"),
                },
                status=400,
            )

        items_data: list[dict[str, Any]] = []
        errors = []
        any_received = False

        for item in items:
            qty_key = f"item_{item.pk}"
            price_key = f"price_{item.pk}"
            notes_key = f"notes_{item.pk}"

            try:
                qty = Decimal(request.POST.get(qty_key, "0") or "0")
            except InvalidOperation:
                qty = Decimal("0")

            try:
                price = Decimal(
                    request.POST.get(price_key, str(item.unit_price))
                    or str(item.unit_price)
                )
            except InvalidOperation:
                price = item.unit_price

            if qty < 0:
                errors.append(f"Quantity for {item.item.name} cannot be negative.")
                continue
            if qty > item.remaining_qty:
                errors.append(
                    f"Quantity for {item.item.name} ({qty}) exceeds remaining ({item.remaining_qty})."
                )
                continue
            if qty > 0:
                any_received = True
                items_data.append(
                    {
                        "item_id": item.item_id,
                        "po_item_id": item.pk,
                        "quantity_ordered_on_po": item.quantity_ordered,
                        "quantity_received": qty,
                        "unit_price_at_receipt": price,
                        "item_notes": request.POST.get(notes_key, ""),
                    }
                )

        if errors:
            for e in errors:
                form.add_error(None, e)
        elif not any_received:
            form.add_error(
                None, "Enter at least one received quantity greater than zero."
            )

        if form.errors:
            return render(
                request,
                self.template_name,
                {
                    "step": "enter_quantities",
                    "po": po,
                    "items": items,
                    "form": form,
                    "open_pos": open_pos,
                    "today": date.today().strftime("%Y-%m-%d"),
                },
                status=400,
            )

        grn_data: dict[str, Any] = {
            "po_id": po.pk,
            "supplier_id": po.supplier_id,
            "received_date": form.cleaned_data["received_date"],
            "notes": form.cleaned_data.get("notes"),
            "received_by_user_id": getattr(request.user, "username", "System"),
        }
        if request.FILES.get("attachment"):
            grn_data["attachment"] = request.FILES["attachment"]

        success, msg, grn_id = goods_receiving_service.create_grn(grn_data, items_data)
        if success:
            messages.success(request, "GRN created successfully.", extra_tags="toast")
            return redirect("grn_detail", pk=grn_id)

        form.add_error(None, msg)
        return render(
            request,
            self.template_name,
            {
                "step": "enter_quantities",
                "po": po,
                "items": items,
                "form": form,
                "open_pos": open_pos,
                "today": date.today().strftime("%Y-%m-%d"),
            },
            status=400,
        )


class GRNDetailView(TemplateView):
    """Display details for a single goods received note."""

    template_name = "inventory/grns/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        grn = get_object_or_404(GoodsReceivedNote, pk=self.kwargs["pk"])
        items = grn.grnitem_set.select_related(
            "po_item", "po_item__item", "po_item__item__unit"
        )
        rows = [
            (
                "PO",
                format_html(
                    '<a class="text-primary" href="{}">{}</a>',
                    reverse("purchase_order_detail", args=[grn.purchase_order_id]),
                    grn.purchase_order_id,
                ),
            ),
            ("Supplier", grn.supplier.name),
            ("Date", grn.received_date),
        ]
        if grn.notes:
            rows.append(("Notes", grn.notes))
        if grn.attachment:
            rows.append(
                (
                    "Attachment",
                    format_html(
                        '<a class="text-primary underline" href="{}">{}</a>',
                        grn.attachment.url,
                        "Download",
                    ),
                )
            )

        # Annotate variance on each item
        items_with_variance = []
        has_discrepancy = False
        for item in items:
            item.variance = item.quantity_received - item.quantity_ordered_on_po
            item.has_discrepancy = item.variance < 0
            if item.has_discrepancy:
                has_discrepancy = True
            items_with_variance.append(item)

        ctx.update(
            {
                "grn": grn,
                "items": items_with_variance,
                "has_discrepancy": has_discrepancy,
                "rows": rows,
                "list_url": reverse("grn_list"),
                "list_title": "GRNs",
                "current_title": f"GRN {grn.pk}",
            }
        )
        return ctx


def grn_export(request, pk: int):
    grn = get_object_or_404(GoodsReceivedNote, pk=pk)
    items = grn.grnitem_set.select_related("po_item", "po_item__item")
    fmt = (request.GET.get("format") or "pdf").lower()
    if fmt == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename=grn_{grn.pk}.csv"
        writer = csv.writer(response)
        writer.writerow(
            ["Item", "Ordered", "Received", "Variance", "Unit Price", "Line Total"]
        )
        for line in items:
            variance = line.quantity_received - line.quantity_ordered_on_po
            writer.writerow(
                [
                    getattr(line.po_item.item, "name", ""),
                    line.quantity_ordered_on_po,
                    line.quantity_received,
                    variance,
                    line.unit_price_at_receipt,
                    line.quantity_received * line.unit_price_at_receipt,
                ]
            )
        return response

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, f"GRN {grn.pk}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(
        0,
        10,
        f"PO: {grn.purchase_order_id}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.cell(
        0,
        10,
        f"Supplier: {getattr(grn.supplier, 'name', '')}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.cell(
        0,
        10,
        f"Date: {grn.received_date}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(4)
    pdf.set_font("Helvetica", size=10)
    pdf.cell(80, 8, "Item", border=1)
    pdf.cell(25, 8, "Ordered", border=1)
    pdf.cell(25, 8, "Received", border=1)
    pdf.cell(25, 8, "Variance", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    for line in items:
        name = getattr(line.po_item.item, "name", "")
        variance = line.quantity_received - line.quantity_ordered_on_po
        pdf.cell(80, 8, str(name), border=1)
        pdf.cell(25, 8, str(line.quantity_ordered_on_po), border=1)
        pdf.cell(25, 8, str(line.quantity_received), border=1)
        pdf.cell(
            25,
            8,
            str(variance),
            border=1,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
    pdf_bytes = bytes(pdf.output())
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=grn_{grn.pk}.pdf"
    return response
