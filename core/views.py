from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import render

from inventory.models import Item

def root_view(request):
    return render(request, "core/home.html")

def health_check(request):
    return HttpResponse("ok")


@login_required
def dashboard(request):
    low_stock = Item.objects.filter(
        reorder_point__isnull=False,
        current_stock__lt=F("reorder_point"),
    ).order_by("name")
    return render(request, "core/dashboard.html", {"low_stock": low_stock})
