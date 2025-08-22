import csv
import logging

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from ..models import GoodsReceivedNote, Supplier

logger = logging.getLogger(__name__)


class GRNListView(TemplateView):
    template_name = "inventory/grns/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request
        grns = GoodsReceivedNote.objects.select_related("purchase_order", "supplier").order_by("-received_date")

        supplier_id = request.GET.get("supplier")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        if supplier_id:
            grns = grns.filter(supplier_id=supplier_id)
        if start_date:
            grns = grns.filter(received_date__gte=start_date)
        if end_date:
            grns = grns.filter(received_date__lte=end_date)

        paginator = Paginator(grns, 20)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        suppliers = Supplier.objects.all()
        query_params = request.GET.copy()
        if "page" in query_params:
            query_params.pop("page")
        querystring = query_params.urlencode()

        ctx.update(
            {
                "grns": page_obj,
                "page_obj": page_obj,
                "suppliers": suppliers,
                "current_supplier": supplier_id,
                "start_date": start_date,
                "end_date": end_date,
                "querystring": querystring,
            }
        )
        return ctx


class GRNDetailView(TemplateView):
    template_name = "inventory/grns/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        grn = get_object_or_404(GoodsReceivedNote, pk=self.kwargs["pk"])
        items = grn.grnitem_set.select_related("po_item", "po_item__item")
        ctx.update({"grn": grn, "items": items})
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
        pdf.cell(30, 8, str(line.quantity_received), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf_bytes = bytes(pdf.output())
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=grn_{grn.pk}.pdf"
    return response
