import logging

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

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
