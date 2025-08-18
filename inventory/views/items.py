import csv
import io
import logging

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from ..models import Item
from ..forms import ItemForm, BulkUploadForm
from ..services import item_service

logger = logging.getLogger(__name__)

_ITEM_ENGINE = None

def _get_item_engine():
    """Return a SQLAlchemy engine for the default Django database."""
    global _ITEM_ENGINE
    if _ITEM_ENGINE is None:
        cfg = settings.DATABASES["default"]
        engine = cfg.get("ENGINE", "")
        if engine.endswith("sqlite3"):
            url = f"sqlite:///{cfg['NAME']}"
        elif "postgresql" in engine:
            url = URL.create(
                "postgresql+psycopg",
                username=cfg.get("USER") or None,
                password=cfg.get("PASSWORD") or None,
                host=cfg.get("HOST") or None,
                port=cfg.get("PORT") or None,
                database=cfg.get("NAME"),
            )
        else:  # pragma: no cover - defensive
            raise ValueError(f"Unsupported database engine: {engine}")
        _ITEM_ENGINE = create_engine(url)
    return _ITEM_ENGINE


class ItemsListView(TemplateView):
    template_name = "inventory/items_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request
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
        ctx.update(
            {
                "q": q,
                "category": category,
                "subcategory": subcategory,
                "active": active,
                "categories": categories,
                "subcategories": subcategories,
            }
        )
        return ctx


class ItemsTableView(TemplateView):
    template_name = "inventory/_items_table.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request
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
        ctx.update(
            {
                "page_obj": page_obj,
                "q": q,
                "category": category,
                "subcategory": subcategory,
                "active": active,
            }
        )
        return ctx


class ItemCreateView(View):
    template_name = "inventory/item_form.html"

    def get(self, request):
        form = ItemForm()
        return render(request, self.template_name, {"form": form, "is_edit": False})

    def post(self, request):
        form = ItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("items_list")
        return render(request, self.template_name, {"form": form, "is_edit": False})


class ItemEditView(View):
    template_name = "inventory/item_form.html"

    def get_object(self, pk: int):
        try:
            return get_object_or_404(Item, pk=pk)
        except (DatabaseError, ValueError):  # pragma: no cover - defensive
            logger.exception("Error retrieving item %s", pk)
            raise Http404("Item not found")

    def get(self, request, pk: int):
        item = self.get_object(pk)
        try:
            form = ItemForm(instance=item)
        except (DatabaseError, ValueError):
            logger.exception("Error loading form for item %s", pk)
            messages.error(request, "Unable to load item")
            return render(
                request,
                self.template_name,
                {"form": None, "is_edit": True, "item": item},
            )
        ctx = {"form": form, "is_edit": True, "item": item}
        return render(request, self.template_name, ctx)

    def post(self, request, pk: int):
        item = self.get_object(pk)
        try:
            form = ItemForm(request.POST, instance=item)
        except (DatabaseError, ValueError):
            logger.exception("Error loading form for item %s", pk)
            messages.error(request, "Unable to load item")
            return render(
                request,
                self.template_name,
                {"form": None, "is_edit": True, "item": item},
            )
        if form.is_valid():
            try:
                form.save()
                return redirect("items_list")
            except (ValidationError, DatabaseError):
                messages.error(request, "Unable to save item")
        ctx = {"form": form, "is_edit": True, "item": item}
        return render(request, self.template_name, ctx)


class ItemSuggestView(TemplateView):
    template_name = "inventory/_item_suggest_fields.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        name = (self.request.GET.get("name") or "").strip()
        base, purchase, category = item_service.suggest_category_and_units(
            _get_item_engine(), name
        )
        ctx.update(
            {"base": base or "", "purchase": purchase or "", "category": category or ""}
        )
        return ctx


class ItemsBulkUploadView(View):
    template_name = "inventory/bulk_upload.html"

    def get(self, request):
        form = BulkUploadForm()
        ctx = {
            "form": form,
            "inserted": 0,
            "errors": [],
            "title": "Bulk Upload Items",
            "back_url": "items_list",
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        inserted = 0
        errors: list[str] = []
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
        ctx = {
            "form": form,
            "inserted": inserted,
            "errors": errors,
            "title": "Bulk Upload Items",
            "back_url": "items_list",
        }
        return render(request, self.template_name, ctx)
