import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import DatabaseError, transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

from ..forms import IndentForm, IndentItemFormSet
from ..indent_pdf import generate_indent_pdf
from ..models import Indent

logger = logging.getLogger(__name__)

INDENT_STATUS_BADGES = {
    "SUBMITTED": "bg-gray-200 text-gray-800",
    "PROCESSING": "bg-blue-200 text-blue-800",
    "COMPLETED": "bg-green-200 text-green-800",
    "CANCELLED": "bg-red-200 text-red-800",
}


class IndentsListView(TemplateView):
    template_name = "inventory/indents_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        status = (self.request.GET.get("status") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        ctx.update({"status": status, "q": q})
        return ctx


class IndentsTableView(TemplateView):
    template_name = "inventory/_indents_table.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        status = (self.request.GET.get("status") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        qs = Indent.objects.all()
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(mrn__icontains=q)
                | Q(requested_by__icontains=q)
                | Q(department__icontains=q)
            )
        qs = qs.order_by("-indent_id")
        paginator = Paginator(qs, 25)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        ctx.update(
            {
                "page_obj": page_obj,
                "status": status,
                "q": q,
                "badges": INDENT_STATUS_BADGES,
            }
        )
        return ctx


class IndentCreateView(View):
    template_name = "inventory/indent_form.html"

    def get(self, request):
        form = IndentForm()
        formset = IndentItemFormSet(prefix="items")
        return render(request, self.template_name, {"form": form, "formset": formset})

    def post(self, request):
        form = IndentForm(request.POST)
        formset = IndentItemFormSet(request.POST, prefix="items")
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    indent = form.save()
                    formset.instance = indent
                    formset.save()
                return redirect("indent_detail", pk=indent.pk)
            except DatabaseError:
                messages.error(request, "Unable to save indent")
        return render(request, self.template_name, {"form": form, "formset": formset})


def indent_detail(request, pk: int):
    indent = get_object_or_404(Indent, pk=pk)
    items = indent.indentitem_set.select_related("item").all()
    return render(
        request,
        "inventory/indent_detail.html",
        {"indent": indent, "items": items, "badges": INDENT_STATUS_BADGES},
    )


@require_POST
@csrf_protect
def indent_update_status(request, pk: int, status: str):
    indent = get_object_or_404(Indent, pk=pk)
    indent.status = status.upper()
    indent.save()
    return redirect("indent_detail", pk=pk)


def indent_pdf(request, pk: int):
    indent = get_object_or_404(Indent, pk=pk)
    items = indent.indentitem_set.select_related("item").all()
    pdf_bytes = generate_indent_pdf(indent, items)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    filename = f"indent_{indent.pk}.pdf"
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response
