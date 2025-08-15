from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponse

from .models import Item, Supplier, StockTransaction
from .forms import (
    ItemForm,
    BulkUploadForm,
    BulkDeleteForm,
    SupplierForm,
    StockReceivingForm,
    StockAdjustmentForm,
    StockWastageForm,
    StockBulkUploadForm,
)

import csv
import io


def items_list(request):
    q = (request.GET.get("q") or "").strip()
    category = (request.GET.get("category") or "").strip()
    subcategory = (request.GET.get("subcategory") or "").strip()
    active = (request.GET.get("active") or "").strip()

    categories = (
        Item.objects.exclude(category__isnull=True)
        .exclude(category="")
        .order_by("category")
        .values_list("category", flat=True)
        .distinct()
    )
    subcategories = (
        Item.objects.exclude(sub_category__isnull=True)
        .exclude(sub_category="")
        .order_by("sub_category")
        .values_list("sub_category", flat=True)
        .distinct()
    )

    ctx = {
        "q": q,
        "category": category,
        "subcategory": subcategory,
        "active": active,
        "categories": categories,
        "subcategories": subcategories,
    }
    return render(request, "inventory/items_list.html", ctx)


def items_table(request):
    q = (request.GET.get("q") or "").strip()
    category = (request.GET.get("category") or "").strip()
    subcategory = (request.GET.get("subcategory") or "").strip()
    active = (request.GET.get("active") or "").strip()

    qs = Item.objects.all()
    if q:
        qs = qs.filter(name__icontains=q)
    if category:
        qs = qs.filter(category=category)
    if subcategory:
        qs = qs.filter(sub_category=subcategory)
    if active:
        if active == "1":
            qs = qs.filter(is_active=True)
        elif active == "0":
            qs = qs.filter(is_active=False)
    qs = qs.order_by("name")
    paginator = Paginator(qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    ctx = {
        "page_obj": page_obj,
        "q": q,
        "category": category,
        "subcategory": subcategory,
        "active": active,
    }
    return render(request, "inventory/_items_table.html", ctx)


def item_create(request):
    if request.method == "POST":
        form = ItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("items_list")
    else:
        form = ItemForm()
    return render(request, "inventory/item_form.html", {"form": form, "is_edit": False})


def item_edit(request, pk: int):
    item = get_object_or_404(Item, pk=pk)
    if request.method == "POST":
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect("items_list")
    else:
        form = ItemForm(instance=item)
    ctx = {"form": form, "is_edit": True, "item": item}
    return render(request, "inventory/item_form.html", ctx)


def items_bulk_upload(request):
    inserted = 0
    errors: list[str] = []
    if request.method == "POST":
        form = BulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]
            data = io.StringIO(file.read().decode("utf-8"))
            reader = csv.DictReader(data)
            for row in reader:
                form_row = ItemForm(row)
                if form_row.is_valid():
                    form_row.save()
                    inserted += 1
                else:
                    errors.append(str(form_row.errors))
    else:
        form = BulkUploadForm()
    ctx = {
        "form": form,
        "inserted": inserted,
        "errors": errors,
        "title": "Bulk Upload Items",
        "back_url": "items_list",
    }
    return render(request, "inventory/bulk_upload.html", ctx)


def suppliers_list(request):
    q = (request.GET.get("q") or "").strip()
    show_inactive = (request.GET.get("show_inactive") or "").strip()
    return render(
        request,
        "inventory/suppliers_list.html",
        {"q": q, "show_inactive": show_inactive},
    )


def suppliers_table(request):
    q = (request.GET.get("q") or "").strip()
    show_inactive = (request.GET.get("show_inactive") or "").strip()
    qs = Supplier.objects.all()
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(contact_person__icontains=q)
            | Q(email__icontains=q)
        )
    if not show_inactive:
        qs = qs.filter(is_active=True)
    qs = qs.order_by("name")
    paginator = Paginator(qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    ctx = {"page_obj": page_obj, "q": q, "show_inactive": show_inactive}
    return render(request, "inventory/_suppliers_table.html", ctx)


def supplier_create(request):
    if request.method == "POST":
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("suppliers_list")
    else:
        form = SupplierForm()
    return render(
        request,
        "inventory/supplier_form.html",
        {"form": form, "is_edit": False},
    )


def supplier_edit(request, pk: int):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == "POST":
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            return redirect("suppliers_list")
    else:
        form = SupplierForm(instance=supplier)
    ctx = {"form": form, "is_edit": True, "supplier": supplier}
    return render(request, "inventory/supplier_form.html", ctx)


def supplier_toggle_active(request, pk: int):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.is_active = not bool(supplier.is_active)
    supplier.save()
    return suppliers_table(request)


def suppliers_bulk_upload(request):
    inserted = 0
    errors: list[str] = []
    if request.method == "POST":
        form = BulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]
            data = io.StringIO(file.read().decode("utf-8"))
            reader = csv.DictReader(data)
            for row in reader:
                form_row = SupplierForm(row)
                if form_row.is_valid():
                    form_row.save()
                    inserted += 1
                else:
                    errors.append(str(form_row.errors))
    else:
        form = BulkUploadForm()
    ctx = {
        "form": form,
        "inserted": inserted,
        "errors": errors,
        "title": "Bulk Upload Suppliers",
        "back_url": "suppliers_list",
    }
    return render(request, "inventory/bulk_upload.html", ctx)


def suppliers_bulk_delete(request):
    deleted = 0
    errors: list[str] = []
    if request.method == "POST":
        form = BulkDeleteForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]
            data = io.StringIO(file.read().decode("utf-8"))
            reader = csv.DictReader(data)
            for row in reader:
                name = (row.get("name") or "").strip()
                if name:
                    qs = Supplier.objects.filter(name=name)
                    count, _ = qs.delete()
                    if count:
                        deleted += count
                    else:
                        errors.append(f"Supplier '{name}' not found")
                else:
                    errors.append("Missing name")
    else:
        form = BulkDeleteForm()
    ctx = {
        "form": form,
        "deleted": deleted,
        "errors": errors,
        "title": "Bulk Delete Suppliers",
        "back_url": "suppliers_list",
    }
    return render(request, "inventory/bulk_delete.html", ctx)


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
                receive_form.save()
                messages.success(request, "Receiving transaction recorded")
                return redirect("stock_movements")
            active = "receive"
        elif "submit_adjust" in request.POST:
            adjust_form = StockAdjustmentForm(request.POST, prefix="adjust")
            if adjust_form.is_valid():
                adjust_form.save()
                messages.success(request, "Adjustment transaction recorded")
                return redirect("stock_movements" + "?section=adjust")
            active = "adjust"
        elif "submit_waste" in request.POST:
            waste_form = StockWastageForm(request.POST, prefix="waste")
            if waste_form.is_valid():
                waste_form.save()
                messages.success(request, "Wastage transaction recorded")
                return redirect("stock_movements" + "?section=waste")
            active = "waste"
        elif "bulk_upload" in request.POST:
            bulk_form = StockBulkUploadForm(request.POST, request.FILES)
            bulk_success_count = 0
            bulk_errors = []
            if bulk_form.is_valid():
                file = bulk_form.cleaned_data["file"]
                data = io.StringIO(file.read().decode("utf-8"))
                reader = csv.DictReader(data)
                for idx, row in enumerate(reader):
                    try:
                        StockTransaction.objects.create(
                            item_id=row.get("item_id") or None,
                            quantity_change=float(row.get("quantity_change") or 0),
                            transaction_type=row.get("transaction_type"),
                            user_id=row.get("user_id"),
                            related_mrn=row.get("related_mrn"),
                            related_po_id=row.get("related_po_id") or None,
                            notes=row.get("notes"),
                        )
                        bulk_success_count += 1
                    except Exception as exc:  # pylint: disable=broad-except
                        bulk_errors.append(f"Row {idx}: {exc}")
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
        .values_list("user_id", flat=True)
        .order_by("user_id")
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
