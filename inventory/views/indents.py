import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import DatabaseError, transaction
from django.db.models import BooleanField, Case, Q, Value, When
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from ..forms.indent_forms import IndentForm, IndentItemFormSet
from ..indent_pdf import generate_indent_pdf
from ..models import Indent

logger = logging.getLogger(__name__)

INDENT_STATUS_BADGES = {
    "PENDING": "badge-warning",
    "APPROVED": "badge-success",
    "SUBMITTED": "badge-warning",
    "PROCESSING": "badge-warning",
    "COMPLETED": "badge-success",
    "CANCELLED": "badge-error",
}


class IndentsListView(TemplateView):
    """Show search and filter options for indents.

    GET params:
        status: filter by indent status.
        q: search term for MRN, requester or department.
    Template: inventory/indents_list.html.
    """

    template_name = "inventory/indents_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        status = (self.request.GET.get("status") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        total_indents = Indent.objects.count()
        filters = [
            {
                "name": "status",
                "value": status,
                "list_id": "indent-statuses",
                "options": [
                    {"value": "", "label": "All Statuses"},
                    {"value": "SUBMITTED", "label": "Submitted"},
                    {"value": "PROCESSING", "label": "Processing"},
                    {"value": "COMPLETED", "label": "Completed"},
                    {"value": "CANCELLED", "label": "Cancelled"},
                ],
            }
        ]
        ctx.update(
            {
                "status": status,
                "q": q,
                "total_indents": total_indents,
                "filters": filters,
            }
        )
        return ctx


class IndentsTableView(TemplateView):
    """Render the paginated table of indents.

    GET params:
        status and q: same filters as the list view.
        page: page number for pagination.
    Template: inventory/_indents_table.html.
    """

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
        today = timezone.now().date()
        qs = qs.annotate(
            is_overdue=Case(
                When(
                    Q(date_required__lt=today)
                    & ~Q(status__in=["COMPLETED", "APPROVED"]),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            )
        ).order_by("-indent_id")
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
    """Handle creation of a new indent with item lines.

    GET renders an empty indent form and formset.
    POST expects IndentForm and IndentItemFormSet data.
    Template: inventory/indent_form.html.
    """

    template_name = "inventory/indent_form.html"

    def get(self, request):
        form = IndentForm()
        suggest_url = reverse("item_search")
        formset = IndentItemFormSet(
            prefix="items", form_kwargs={"item_suggest_url": suggest_url}
        )
        return render(request, self.template_name, {"form": form, "formset": formset})

    def post(self, request):
        form = IndentForm(request.POST)
        suggest_url = reverse("item_search")
        formset = IndentItemFormSet(
            request.POST,
            prefix="items",
            form_kwargs={"item_suggest_url": suggest_url},
        )
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
    badge_class = INDENT_STATUS_BADGES.get(indent.status.upper(), "")
    rows = [
        (
            "Status",
            format_html(
                '<span class="px-2 py-1 rounded {}">{}</span>',
                badge_class,
                indent.status,
            ),
        ),
        ("Requested By", indent.requested_by),
        ("Department", indent.department),
    ]
    ctx = {"indent": indent, "items": items, "rows": rows}
    return render(request, "inventory/indent_detail.html", ctx)


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
