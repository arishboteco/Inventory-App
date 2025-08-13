from django.core.paginator import Paginator
from django.shortcuts import render

from .models import Item


def items_list(request):
    """Render the items search page."""
    return render(request, "inventory/items_list.html")


def items_table(request):
    """Render the items table partial with optional search and pagination."""
    q = request.GET.get("q", "")
    items = Item.objects.all()
    if q:
        items = items.filter(name__icontains=q)
    items = items.order_by("name")

    paginator = Paginator(items, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "q": q,
    }
    return render(request, "inventory/_items_table.html", context)
