import csv
import logging

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.html import format_html
from django.views.generic import TemplateView
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from ..forms.purchase_forms import GRNForm
from ..models import GoodsReceivedNote, PurchaseOrder, Supplier
from ..services import goods_receiving_service, list_utils

logger = logging.getLogger(__name__)


class GRNListView(TemplateView):
    """List goods received notes with filter and sort options.

    GET params:
        supplier: supplier ID to filter by.
        start_date, end_date: restrict by received date range.
        sort, direction: control ordering of results.
    Template: inventory/grns/list.html.
    """

    template_name = "inventory/grns/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request
        grns = GoodsReceivedNote.objects.select_related("purchase_order", "supplier")
        filters = {
            "supplier": "supplier_id",
            "start_date": "received_date__gte",
            "end_date": "received_date__lte",
        }
        allowed_sorts = {"received_date"}
        grns, params = list_utils.apply_filters_sort(
            request,
            grns,
            filter_fields=filters,
            allowed_sorts=allowed_sorts,
            default_sort="received_date",
            default_direction="desc",
        )
        page_obj, _ = list_utils.paginate(request, grns, default_page_size=20)
        suppliers = Supplier.objects.all()
        querystring = list_utils.build_querystring(request)
        ctx.update(
            {
                "grns": page_obj,
                "page_obj": page_obj,
                "suppliers": suppliers,
                "querystring": querystring,
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
                success, msg, _ = goods_receiving_service.create_grn(
                    grn_data, items_data
                )
                if success:
                    messages.success(request, "GRN created", extra_tags="toast")
                    return redirect("grn_list")
                messages.error(request, msg, extra_tags="toast")
        ctx = self.get_context_data(quick_form=form)
        return self.render_to_response(ctx)


class GRNDetailView(TemplateView):
    """Display details for a single goods received note.

    Template: inventory/grns/detail.html.
    """

    template_name = "inventory/grns/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        grn = get_object_or_404(GoodsReceivedNote, pk=self.kwargs["pk"])
        items = grn.grnitem_set.select_related("po_item", "po_item__item")
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
        ctx.update(
            {
                "grn": grn,
                "items": items,
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
        writer.writerow(["Item", "Ordered", "Received"])
        for line in items:
            writer.writerow(
                [
                    getattr(line.po_item.item, "name", ""),
                    line.po_item.quantity_ordered,
                    line.quantity_received,
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
    pdf.cell(100, 8, "Item", border=1)
    pdf.cell(30, 8, "Ordered", border=1)
    pdf.cell(30, 8, "Received", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    for line in items:
        name = getattr(line.po_item.item, "name", "")
        pdf.cell(100, 8, str(name), border=1)
        pdf.cell(30, 8, str(line.po_item.quantity_ordered), border=1)
        pdf.cell(
            30,
            8,
            str(line.quantity_received),
            border=1,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
    pdf_bytes = bytes(pdf.output())
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=grn_{grn.pk}.pdf"
    return response
