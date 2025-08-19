import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from ..models import GoodsReceivedNote

logger = logging.getLogger(__name__)


class GRNListView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/grns/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["grns"] = GoodsReceivedNote.objects.select_related("purchase_order", "supplier").order_by("-received_date")
        return ctx


class GRNDetailView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/grns/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        grn = get_object_or_404(GoodsReceivedNote, pk=self.kwargs["pk"])
        items = grn.grnitem_set.select_related("po_item", "po_item__item")
        ctx.update({"grn": grn, "items": items})
        return ctx
