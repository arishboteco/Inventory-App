from django.shortcuts import render
from django.core.paginator import Paginator

from .models import Item


def items_list(request):
    return render(request, "inventory/items_list.html")


def items_table(request):
    q = (request.GET.get("q") or "").strip()
    qs = Item.objects.all()
    if q:
        qs = qs.filter(name__icontains=q)
    qs = qs.order_by("name")
    paginator = Paginator(qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    ctx = {"page_obj": page_obj, "q": q}
    return render(request, "inventory/_items_table.html", ctx)
