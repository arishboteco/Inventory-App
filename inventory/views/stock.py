import csv
import io
from collections import defaultdict
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import TemplateView

from inventory.models import Item

from ..forms.stock_forms import (
    StockAdjustmentForm,
    StockBulkUploadForm,
    StockReceivingForm,
    StockWastageForm,
)
from ..models import StockTransaction
from ..models.orders import PurchaseOrder
from ..services import stock_service
from ..services.exceptions import StockServiceError


def stock_movements(request):

    sections = {
        "receive": "Goods Received",
        "adjust": "Stock Adjustment",
        "waste": "Wastage/Spoilage",
    }
    active = request.GET.get("section", "receive")

    item_url = reverse("item_search")

    receive_form = StockReceivingForm(prefix="receive", item_suggest_url=item_url)
    adjust_form = StockAdjustmentForm(prefix="adjust", item_suggest_url=item_url)
    waste_form = StockWastageForm(prefix="waste", item_suggest_url=item_url)
    quick_form = StockAdjustmentForm(prefix="quick", item_suggest_url=item_url)
    reopen_modal: str | None = None
    bulk_form = StockBulkUploadForm()
    bulk_success_count = None
    bulk_errors: list[str] | None = None

    def _display_item_name(form):
        if not form.is_bound:
            return
        key = form.add_prefix("item")
        try:
            raw = (form.data.get(key) or "").strip()
        except Exception:
            return
        if raw.isdigit():
            item = Item.objects.filter(pk=int(raw)).only("name").first()
            if item:
                data = form.data.copy()
                try:
                    # QueryDict
                    data[key] = f"{item.pk} - {item.name}"
                except Exception:
                    pass
                form.data = data

    def _flash_form(which: str, form):
        data = {}
        try:
            data = form.data.dict()
        except Exception:
            # Fallback best-effort
            try:
                data = {k: v for k, v in form.data.items()}
            except Exception:
                data = {}
        request.session["stock_form_flash"] = {
            "which": which,
            "data": data,
            "errors": form.errors.get_json_data(),
        }

    def _hydrate_from_flash():
        nonlocal receive_form, adjust_form, waste_form, reopen_modal
        payload = request.session.pop("stock_form_flash", None)
        if not payload:
            return
        which = payload.get("which")
        data = payload.get("data") or {}
        errors = payload.get("errors") or {}
        if which == "receive":
            receive_form = StockReceivingForm(
                data, prefix="receive", item_suggest_url=item_url
            )
            for field, items in errors.items():
                for e in items:
                    receive_form.add_error(
                        None if field == "__all__" else field, e.get("message")
                    )
            _display_item_name(receive_form)
            reopen_modal = "receive"
        elif which == "adjust":
            adjust_form = StockAdjustmentForm(
                data, prefix="adjust", item_suggest_url=item_url
            )
            for field, items in errors.items():
                for e in items:
                    adjust_form.add_error(
                        None if field == "__all__" else field, e.get("message")
                    )
            _display_item_name(adjust_form)
            reopen_modal = "adjust"
        elif which == "waste":
            waste_form = StockWastageForm(
                data, prefix="waste", item_suggest_url=item_url
            )
            for field, items in errors.items():
                for e in items:
                    waste_form.add_error(
                        None if field == "__all__" else field, e.get("message")
                    )
            _display_item_name(waste_form)
            reopen_modal = "waste"

    if request.method == "POST":
        if "submit_receive" in request.POST:
            receive_form = StockReceivingForm(
                request.POST, prefix="receive", item_suggest_url=item_url
            )
            if receive_form.is_valid():
                cd = receive_form.cleaned_data
                try:
                    stock_service.record_stock_transaction(
                        item_id=cd["item"].pk,
                        quantity_change=cd["quantity_change"],
                        transaction_type="RECEIVING",
                        user_id=(getattr(request.user, "username", None) or "System"),
                        user_int=(getattr(request.user, "pk", None) or None),
                        related_po_id=(
                            cd.get("related_po").pk if cd.get("related_po") else None
                        ),
                        notes=cd.get("notes"),
                        transaction_date=cd.get("transaction_date") or None,
                    )
                    messages.success(
                        request, "Receiving transaction recorded", extra_tags="toast"
                    )
                    return redirect("stock_movements")
                except StockServiceError as exc:
                    msg = str(exc)
                    if "not found" in msg.lower():
                        receive_form.add_error(
                            "item", "Choose a valid item from the list."
                        )
                    else:
                        receive_form.add_error(None, msg)
                    _flash_form("receive", receive_form)
                    return redirect(reverse("stock_movements") + "?section=receive")
            else:
                _flash_form("receive", receive_form)
                return redirect(reverse("stock_movements") + "?section=receive")
        elif "submit_adjust" in request.POST:
            adjust_form = StockAdjustmentForm(
                request.POST, prefix="adjust", item_suggest_url=item_url
            )
            if adjust_form.is_valid():
                cd = adjust_form.cleaned_data
                try:
                    stock_service.record_stock_transaction(
                        item_id=cd["item"].pk,
                        quantity_change=cd["quantity_change"],
                        transaction_type="ADJUSTMENT",
                        user_id=(getattr(request.user, "username", None) or "System"),
                        user_int=(getattr(request.user, "pk", None) or None),
                        notes=cd.get("notes"),
                        reason_category=cd.get("reason_category") or None,
                        transaction_date=cd.get("transaction_date") or None,
                    )
                    messages.success(
                        request, "Adjustment transaction recorded", extra_tags="toast"
                    )
                    return redirect(reverse("stock_movements") + "?section=adjust")
                except StockServiceError as exc:
                    msg = str(exc)
                    if "not found" in msg.lower():
                        adjust_form.add_error(
                            "item", "Choose a valid item from the list."
                        )
                    else:
                        adjust_form.add_error(None, msg)
                    _flash_form("adjust", adjust_form)
                    return redirect(reverse("stock_movements") + "?section=adjust")
            else:
                _flash_form("adjust", adjust_form)
                return redirect(reverse("stock_movements") + "?section=adjust")
        elif "submit_waste" in request.POST:
            waste_form = StockWastageForm(
                request.POST, prefix="waste", item_suggest_url=item_url
            )
            if waste_form.is_valid():
                cd = waste_form.cleaned_data
                qty = -abs(cd["quantity_change"])
                try:
                    stock_service.record_stock_transaction(
                        item_id=cd["item"].pk,
                        quantity_change=qty,
                        transaction_type="WASTAGE",
                        user_id=(getattr(request.user, "username", None) or "System"),
                        user_int=(getattr(request.user, "pk", None) or None),
                        notes=cd.get("notes"),
                        reason_category=cd.get("reason_category") or None,
                        transaction_date=cd.get("transaction_date") or None,
                    )
                    messages.success(
                        request, "Wastage transaction recorded", extra_tags="toast"
                    )
                    return redirect(reverse("stock_movements") + "?section=waste")
                except StockServiceError as exc:
                    msg = str(exc)
                    if "not found" in msg.lower():
                        waste_form.add_error(
                            "item", "Choose a valid item from the list."
                        )
                    else:
                        waste_form.add_error(None, msg)
                    _flash_form("waste", waste_form)
                    return redirect(reverse("stock_movements") + "?section=waste")
            else:
                _flash_form("waste", waste_form)
                return redirect(reverse("stock_movements") + "?section=waste")
        elif "submit_quick" in request.POST:
            quick_form = StockAdjustmentForm(
                request.POST, prefix="quick", item_suggest_url=item_url
            )
            if quick_form.is_valid():
                cd = quick_form.cleaned_data
                try:
                    stock_service.record_stock_transaction(
                        item_id=cd["item"].pk,
                        quantity_change=cd["quantity_change"],
                        transaction_type="ADJUSTMENT",
                        user_id=cd.get("user_id"),
                        notes=cd.get("notes"),
                    )
                    messages.success(
                        request, "Quick movement recorded", extra_tags="toast"
                    )
                    return redirect("stock_movements")
                except StockServiceError as exc:
                    messages.error(request, str(exc), extra_tags="toast")
            active = "receive"
        elif "bulk_upload" in request.POST:
            bulk_form = StockBulkUploadForm(request.POST, request.FILES)
            bulk_success_count = 0
            bulk_errors = []
            if bulk_form.is_valid():
                file = bulk_form.cleaned_data["file"]
                data = io.StringIO(file.read().decode("utf-8"))
                reader = csv.DictReader(data)
                txs_to_create = []
                for idx, row in enumerate(reader):
                    item_id_str = row.get("item_id", "").strip()
                    quantity_str = row.get("quantity_change", "").strip()

                    if not item_id_str or not quantity_str:
                        bulk_errors.append(
                            f"Row {idx+2}: Missing item_id or quantity_change"
                        )
                        continue

                    try:
                        item_id = int(item_id_str)
                        quantity = Decimal(quantity_str)

                        txs_to_create.append(
                            {
                                "item_id": item_id,
                                "quantity_change": quantity,
                                "transaction_type": row.get(
                                    "transaction_type", "ADJUSTMENT"
                                ).strip(),
                                "user_id": row.get("user_id", "System").strip(),
                                "user_int": (
                                    int(row.get("user_int"))
                                    if row.get("user_int")
                                    else None
                                ),
                                "related_indent_id": (
                                    int(row.get("related_indent_id"))
                                    if row.get("related_indent_id")
                                    else None
                                ),
                                "related_po_id": (
                                    int(row.get("related_po_id"))
                                    if row.get("related_po_id")
                                    else None
                                ),
                                "notes": row.get("notes"),
                            }
                        )
                    except (ValueError, TypeError):
                        bulk_errors.append(
                            (
                                f"Row {idx+2}: Invalid number format for item_id or "
                                "quantity_change"
                            ),
                        )

                if not bulk_errors and txs_to_create:
                    if stock_service.record_stock_transactions_bulk(txs_to_create):
                        bulk_success_count = len(txs_to_create)
                    else:
                        bulk_errors.append(
                            "A database error occurred during the bulk transaction."
                        )
                elif not txs_to_create and not bulk_errors:
                    bulk_errors.append("No valid rows found in the uploaded file.")

            active = request.GET.get("section", "receive")
    # Hydrate any flashed invalid form after PRG
    _hydrate_from_flash()

    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    item_q = request.GET.get("item_q", "").strip()
    tx_type_filter = request.GET.get("type", "").strip()

    qs = StockTransaction.objects.select_related("item").order_by("-transaction_date")
    if date_from:
        qs = qs.filter(transaction_date__date__gte=date_from)
    if date_to:
        qs = qs.filter(transaction_date__date__lte=date_to)
    if item_q:
        qs = qs.filter(item__name__icontains=item_q)
    if tx_type_filter:
        qs = qs.filter(transaction_type=tx_type_filter)

    paginator = Paginator(qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    params = request.GET.copy()
    params.pop("page", None)
    query_string = params.urlencode()

    total_transactions = qs.count()
    pending_orders = PurchaseOrder.objects.filter(
        status__in=["ORDERED", "PARTIAL"]
    ).count()

    tabs = [
        {
            "id": "receive",
            "title": sections["receive"],
            "template": "inventory/_receive_form.html",
        },
        {
            "id": "adjust",
            "title": sections["adjust"],
            "template": "inventory/_adjust_form.html",
        },
        {
            "id": "waste",
            "title": sections["waste"],
            "template": "inventory/_waste_form.html",
        },
    ]
    tabs.sort(key=lambda t: t["id"] != active)

    ctx = {
        "tabs": tabs,
        "receive_form": receive_form,
        "adjust_form": adjust_form,
        "waste_form": waste_form,
        "quick_form": quick_form,
        "bulk_form": bulk_form,
        "bulk_success_count": bulk_success_count,
        "bulk_errors": bulk_errors,
        "page_obj": page_obj,
        "query_string": query_string,
        "open_modal": reopen_modal,
        "active_section": sections.get(active, sections["receive"]),
        "total_transactions": total_transactions,
        "pending_orders": pending_orders,
        "filter_date_from": date_from,
        "filter_date_to": date_to,
        "filter_item_q": item_q,
        "filter_type": tx_type_filter,
    }
    return render(request, "inventory/stock_movements.html", ctx)


class UserSearchView(TemplateView):
    template_name = "inventory/_user_options.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query = (self.request.GET.get("q") or "").strip()
        qs = (
            StockTransaction.objects.exclude(user_id__isnull=True)
            .exclude(user_id="")
            .values_list("user_id", flat=True)
            .distinct()
            .order_by("user_id")
        )
        if query:
            qs = [u for u in qs if query.lower() in (u or "").lower()]
        ctx["users"] = list(qs)[:20]
        return ctx


class POSearchView(TemplateView):
    template_name = "inventory/_po_options.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query = (self.request.GET.get("q") or "").strip()
        pos = PurchaseOrder.objects.only("po_id").order_by("-po_id")
        if query and query.isdigit():
            pos = pos.filter(po_id__icontains=query)
        ctx["pos"] = pos[:20]
        return ctx


def history_reports(request):
    item = (request.GET.get("item") or request.GET.get("q") or "").strip()
    tx_type = (request.GET.get("type") or "").strip()
    user = (request.GET.get("user") or "").strip()
    start_date = (request.GET.get("start_date") or "").strip()
    end_date = (request.GET.get("end_date") or "").strip()
    sort = (request.GET.get("sort") or "date").strip()
    direction = (request.GET.get("direction") or "desc").strip()

    qs = StockTransaction.objects.select_related("item").all()
    if item:
        qs = qs.filter(item__name__icontains=item)
    if tx_type:
        qs = qs.filter(transaction_type=tx_type)
    if user:
        qs = qs.filter(user_id=user)
    if start_date:
        qs = qs.filter(transaction_date__gte=start_date)
    if end_date:
        qs = qs.filter(transaction_date__lte=end_date)

    allowed_sorts = {
        "id": "transaction_id",
        "item": "item__name",
        "type": "transaction_type",
        "qty": "quantity_change",
        "user": "user_id",
        "date": "transaction_date",
    }
    if sort not in allowed_sorts:
        sort = "date"
    ordering = allowed_sorts[sort]
    ordering = ordering if direction != "desc" else f"-{ordering}"
    qs = qs.order_by(ordering)

    total_quantity = qs.aggregate(total=Sum("quantity_change"))["total"] or Decimal("0")

    # Per-type totals (Bug 2)
    totals_qs = qs.values("transaction_type").annotate(total=Sum("quantity_change"))
    total_map = {t["transaction_type"]: float(t["total"] or 0) for t in totals_qs}
    total_received = total_map.get("RECEIVING", 0)
    total_adjusted = total_map.get("ADJUSTMENT", 0)
    total_wastage_val = total_map.get("WASTAGE", 0)

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=history_report.csv"
        writer = csv.writer(response)
        writer.writerow(
            [
                "Transaction ID",
                "Item",
                "Quantity",
                "Type",
                "User",
                "Date",
                "Notes",
            ]
        )
        for row in qs:
            writer.writerow(
                [
                    row.transaction_id,
                    getattr(row.item, "name", ""),
                    row.quantity_change,
                    row.transaction_type,
                    row.user_id,
                    row.transaction_date,
                    row.notes,
                ]
            )
        return response

    if request.GET.get("export") == "pdf":
        from fpdf import FPDF

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=history_report.pdf"

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=10)

        headers = [
            "Transaction ID",
            "Item",
            "Quantity",
            "Type",
            "User",
            "Date",
            "Notes",
        ]
        col_widths = [25, 30, 20, 25, 20, 30, 40]
        for head, width in zip(headers, col_widths):
            pdf.cell(width, 8, head, border=1)
        pdf.ln()

        for row in qs:
            pdf.cell(col_widths[0], 8, str(row.transaction_id), border=1)
            pdf.cell(col_widths[1], 8, getattr(row.item, "name", ""), border=1)
            pdf.cell(col_widths[2], 8, str(row.quantity_change), border=1)
            pdf.cell(col_widths[3], 8, row.transaction_type, border=1)
            pdf.cell(col_widths[4], 8, str(row.user_id), border=1)
            pdf.cell(
                col_widths[5],
                8,
                row.transaction_date.strftime("%Y-%m-%d"),
                border=1,
            )
            pdf.cell(col_widths[6], 8, (row.notes or "")[:40], border=1)
            pdf.ln()

        pdf_bytes = pdf.output(dest="S").encode("latin1")
        response.write(pdf_bytes)
        return response

    paginator = Paginator(qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    transaction_types = (
        StockTransaction.objects.values_list("transaction_type", flat=True)
        .order_by("transaction_type")
        .distinct()
    )
    users = (
        StockTransaction.objects.exclude(user_id__isnull=True)
        .exclude(user_id="")
        .order_by("user_id")
        .values_list("user_id", flat=True)
        .distinct()
    )

    params = request.GET.copy()
    pagination_params = params.copy()
    pagination_params.pop("page", None)
    pagination_params.pop("export", None)
    query_string = pagination_params.urlencode()

    sort_params = pagination_params.copy()
    sort_params.pop("sort", None)
    sort_params.pop("direction", None)
    sort_query = sort_params.urlencode()

    filters = [
        {
            "name": "type",
            "value": tx_type,
            "list_id": "history-types",
            "options": [{"value": "", "label": "All Types"}]
            + [{"value": t} for t in transaction_types],
        },
        {
            "name": "user",
            "value": user,
            "list_id": "history-users",
            "options": [{"value": "", "label": "All Users"}]
            + [{"value": u} for u in users],
        },
    ]

    # 3-series chart data (Bug 1)
    chart_rows = list(
        qs.values("transaction_date", "transaction_type", "quantity_change")
    )
    dates_set = sorted(
        set(
            r["transaction_date"].date().isoformat()
            for r in chart_rows
            if r["transaction_date"]
        )
    )
    receiving_map: defaultdict = defaultdict(float)
    adjust_map: defaultdict = defaultdict(float)
    wastage_map: defaultdict = defaultdict(float)
    for r in chart_rows:
        if not r["transaction_date"]:
            continue
        d = r["transaction_date"].date().isoformat()
        val = float(r["quantity_change"] or 0)
        t = r["transaction_type"]
        if t == "RECEIVING":
            receiving_map[d] += val
        elif t == "ADJUSTMENT":
            adjust_map[d] += val
        elif t == "WASTAGE":
            wastage_map[d] += val
    chart_labels = dates_set
    chart_receiving = [receiving_map[d] for d in dates_set]
    chart_adjust = [adjust_map[d] for d in dates_set]
    chart_wastage = [wastage_map[d] for d in dates_set]

    tabs = [
        {
            "id": "history-table-tab",
            "title": "Table",
            "template": "inventory/_history_table.html",
        },
        {
            "id": "history-chart-tab",
            "title": "Chart",
            "template": "inventory/_history_chart.html",
        },
    ]

    ctx = {
        "page_obj": page_obj,
        "transaction_types": transaction_types,
        "users": users,
        "item": item,
        "type": tx_type,
        "user": user,
        "start_date": start_date,
        "end_date": end_date,
        "query_string": query_string,
        "sort_query": sort_query,
        "sort": sort,
        "direction": direction,
        "total_quantity": total_quantity,
        "total_received": total_received,
        "total_adjusted": total_adjusted,
        "total_wastage_val": total_wastage_val,
        "filters": filters,
        "chart_labels": chart_labels,
        "chart_receiving": chart_receiving,
        "chart_adjust": chart_adjust,
        "chart_wastage": chart_wastage,
        "tabs": tabs,
        "list_url": reverse("root"),
        "list_title": "Dashboard",
        "current_title": "Reports",
    }
    template = (
        "inventory/_history_tabs.html"
        if request.headers.get("HX-Request")
        else "inventory/history_reports.html"
    )
    return render(request, template, ctx)
