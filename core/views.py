from django.contrib.auth.decorators import login_required
from django.db.models import F, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import render

from inventory.models import Item


def root_view(request):
    return render(request, "core/home.html")


def health_check(request):
    return HttpResponse("ok")


@login_required
def dashboard(request):
    # Use Coalesce to safely handle potential NULL values in the database,
    # treating them as 0.0 for the comparison. This prevents the 500 error.
    low_stock = Item.objects.annotate(
        stock_safe=Coalesce("current_stock", Value(0.0)),
        reorder_safe=Coalesce("reorder_point", Value(0.0))
    ).filter(
        reorder_safe__gt=0,  # Only consider items with a reorder point > 0
        stock_safe__lt=F("reorder_safe")
    ).order_by("name")
    
    return render(request, "core/dashboard.html", {"low_stock": low_stock})
