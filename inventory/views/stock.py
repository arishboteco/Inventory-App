import csv
import io

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render

from ..forms import (
    StockReceivingForm,
    StockAdjustmentForm,
    StockWastageForm,
    StockBulkUploadForm,
)
from ..models import StockTransaction, Item
from ..services import stock_service


def stock_movements(request):
    sections = {
        "receive": "Goods Received",
        "adjust": "Stock Adjustment",
        "waste": "Wastage/Spoilage",
    }
    active = request.GET.get("section", "receive")

    receive_form = StockReceivingForm(prefix="receive")
    adjust_form = StockAdjustmentForm(prefix="adjust")
    waste_form = StockWastageForm(prefix="waste")
    bulk_form = StockBulkUploadForm()
    bulk_success_count = None
    bulk_errors: list[str] | None = None

    if request.method == "POST":
        if "submit_receive" in request.POST:
            receive_form = StockReceivingForm(request.POST, prefix="receive")
            if receive_form.is_valid():
                cd = receive_form.cleaned_data
                ok = stock_service.record_stock_transaction(
                    item_id=cd["item"].pk,
                    quantity_change=cd["quantity_change"],
                    transaction_type="RECEIVING",
                    user_id=cd.get("user_id"),
                    related_po_id=cd.get("related_po_id"),
                    notes=cd.get("notes"),
                )
                if ok:
                    messages.success(request, "Receiving transaction recorded")
                    return redirect("stock_movements")
                messages.error(request, "Failed to record transaction")
            active = "receive"
        elif "submit_adjust" in request.POST:
            adjust_form = StockAdjustmentForm(request.POST, prefix="adjust")
            if adjust_form.is_valid():
                cd = adjust_form.cleaned_data
                ok = stock_service.record_stock_transaction(
                    item_id=cd["item"].pk,
                    quantity_change=cd["quantity_change"],
                    transaction_type="ADJUSTMENT",
                    user_id=cd.get("user_id"),
                    notes=cd.get("notes"),
                )
                if ok:
                    messages.success(request, "Adjustment transaction recorded")
                    return redirect("stock_movements" + "?section=adjust")
                messages.error(request, "Failed to record transaction")
            active = "adjust"
        elif "submit_waste" in request.POST:
            waste_form = StockWastageForm(request.POST, prefix="waste")
            if waste_form.is_valid():
                cd = waste_form.cleaned_data
                qty = -abs(cd["quantity_change"])
                ok = stock_service.record_stock_transaction(
                    item_id=cd["item"].pk,
                    quantity_change=qty,
                    transaction_type="WASTAGE",
                    user_id=cd.get("user_id"),
                    notes=cd.get("notes"),
                )
                if ok:
                    messages.success(request, "Wastage transaction recorded")
                    return redirect("stock_movements" + "?section=waste")
                messages.error(request, "Failed to record transaction")
            active = "waste"
        elif "bulk_upload" in request.POST:
            bulk_form = StockBulkUploadForm(request.POST, request.FILES)
            bulk_success_count = 0
            bulk_errors = []
            if bulk_form.is_valid():
                file = bulk_form.cleaned_data["file"]
                data = io.StringIO(file.read().decode("utf-8"))
                reader = csv.DictReader(data)
                txs = []
                for idx, row in enumerate(reader):
                    try:
                        txs.append(
                            {
                                "item_id": int(row.get("item_id")),
                                "quantity_change": float(row.get("quantity_change")),
                                "transaction_type": row.get("transaction_type", ""),
                                "user_id": row.get("user_id"),
                                "related_mrn": row.get("related_mrn"),
                                "related_po_id": (
                                    int(row.get("related_po_id"))
                                    if row.get("related_po_id")
                                    else None
                                ),
                                "notes": row.get("notes"),
                            }
                        )
                    except Exception as exc:  # pylint: disable=broad-except
                        bulk_errors.append(f"Row {idx}: {exc}")
                if txs and stock_service.record_stock_transactions_bulk(txs):
                    bulk_success_count = len(txs)
                else:
                    bulk_errors.append("Failed to record bulk transactions")
            active = request.GET.get("section", "receive")

    ctx = {
        "sections": sections,
        "active_section": active,
        "receive_form": receive_form,
        "adjust_form": adjust_form,
        "waste_form": waste_form,
        "bulk_form": bulk_form,
        "bulk_success_count": bulk_success_count,
        "bulk_errors": bulk_errors,
    }
    return render(request, "inventory/stock_movements.html", ctx)


def history_reports(request):
    item = (request.GET.get("item") or "").strip()
    tx_type = (request.GET.get("type") or "").strip()
    user = (request.GET.get("user") or "").strip()
    start_date = (request.GET.get("start_date") or "").strip()
    end_date = (request.GET.get("end_date") or "").strip()

    qs = StockTransaction.objects.select_related("item").all()
    if item:
        qs = qs.filter(item_id=item)
    if tx_type:
        qs = qs.filter(transaction_type=tx_type)
    if user:
        qs = qs.filter(user_id=user)
    if start_date:
        qs = qs.filter(transaction_date__gte=start_date)
    if end_date:
        qs = qs.filter(transaction_date__lte=end_date)

    qs = qs.order_by("-transaction_date")

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

    paginator = Paginator(qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    items = Item.objects.order_by("name")
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
    params.pop("page", None)
    params.pop("export", None)
    query_string = params.urlencode()

    ctx = {
        "page_obj": page_obj,
        "items": items,
        "transaction_types": transaction_types,
        "users": users,
        "item": item,
        "type": tx_type,
        "user": user,
        "start_date": start_date,
        "end_date": end_date,
        "query_string": query_string,
    }
    return render(request, "inventory/history_reports.html", ctx)
