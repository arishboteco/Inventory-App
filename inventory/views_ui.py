from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Item, Supplier
from .forms import ItemForm, BulkUploadForm

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
    ctx = {"form": form, "inserted": inserted, "errors": errors}
    return render(request, "inventory/bulk_upload.html", ctx)


def suppliers_list(request):
    q = (request.GET.get("q") or "").strip()
    return render(request, "inventory/suppliers_list.html", {"q": q})


def suppliers_table(request):
    q = (request.GET.get("q") or "").strip()
    qs = Supplier.objects.all()
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(email__icontains=q)
            | Q(phone__icontains=q)
            | Q(contact_person__icontains=q)
        )
    qs = qs.order_by("name")
    paginator = Paginator(qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    ctx = {"page_obj": page_obj, "q": q}
    return render(request, "inventory/_suppliers_table.html", ctx)
