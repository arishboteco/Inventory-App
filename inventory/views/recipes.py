from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from ..forms.recipe_forms import RecipeForm, RecipeItemFormSet
from ..models import Recipe, RecipeItem
from ..services import list_utils, recipe_service
from ..services.units_service import UnitsService


def _filtered_recipes_queryset(request):
    """Return the recipe queryset filtered, searched and sorted for tables/cards."""

    qs = Recipe.objects.annotate(item_count=Count("items"))
    qs, params = list_utils.apply_filters_sort(
        request,
        qs,
        search_fields=["name", "description"],
        filter_fields={"active": "is_active"},
        allowed_sorts=["name", "type", "default_yield_unit", "is_active"],
        default_sort="name",
    )
    params.setdefault("q", "")
    params["recipe_count"] = qs.count()
    return qs, params


def _get_field_label(form_like, field_name):
    field = getattr(form_like, "fields", {}).get(field_name)
    if field and getattr(field, "label", None):
        return str(field.label)
    return field_name.replace("_", " ").capitalize()


def _build_form_error_payload(form, formset):
    """Collect validation errors into a friendly JSON payload."""

    form_non_field_errors = [str(error) for error in form.non_field_errors()]
    formset_non_form_errors = [str(error) for error in formset.non_form_errors()]

    form_errors = {}
    first_form_field_error = None
    for field_name, errors in form.errors.items():
        error_texts = [str(error) for error in errors]
        if not error_texts:
            continue
        form_errors[field_name] = error_texts
        if first_form_field_error is None:
            label = _get_field_label(form, field_name)
            first_form_field_error = f"{label}: {error_texts[0]}"

    formset_errors = []
    first_formset_field_error = None
    forms = list(formset.forms)
    total_forms = len(forms)
    for index, form_instance in enumerate(forms):
        child_errors = {}
        for field_name, errors in form_instance.errors.items():
            error_texts = [str(error) for error in errors]
            if not error_texts:
                continue
            child_errors[field_name] = error_texts
            if first_formset_field_error is None:
                label = _get_field_label(form_instance, field_name)
                prefix = f"Row {index + 1} - " if total_forms > 1 else ""
                first_formset_field_error = f"{prefix}{label}: {error_texts[0]}"
        if child_errors:
            formset_errors.append({"index": index, "errors": child_errors})

    message_parts = []
    message_parts.extend(form_non_field_errors)
    message_parts.extend(formset_non_form_errors)
    if first_form_field_error:
        message_parts.append(first_form_field_error)
    if first_formset_field_error:
        message_parts.append(first_formset_field_error)

    if not message_parts:
        message_parts.append("Please correct the highlighted errors and try again.")

    message = " ".join(part.strip() for part in message_parts if part)

    return {
        "ok": False,
        "message": message,
        "errors": {
            "form": form_errors,
            "form_non_field": form_non_field_errors,
            "formset_non_form": formset_non_form_errors,
            "formset": formset_errors,
        },
    }


def _serialize_recipe(recipe):
    """Return a lightweight payload describing a recipe."""

    if recipe is None:
        return {}
    item_count = getattr(recipe, "item_count", None)
    if item_count is None:
        item_count = recipe.items.count()
    qty = getattr(recipe, "default_yield_qty", None)
    image_url = recipe_service.get_plating_image_url(getattr(recipe, "pk", None))
    return {
        "id": recipe.pk,
        "name": recipe.name,
        "url": reverse("recipe_detail", kwargs={"pk": recipe.pk}),
        "is_active": recipe.is_active,
        "type": recipe.type or "",
        "default_yield_qty": float(qty) if qty is not None else None,
        "default_yield_unit": recipe.default_yield_unit or "",
        "item_count": item_count,
        "plating_image_url": image_url,
    }


TWOPLACES = Decimal("0.01")


def _to_decimal(value):
    if isinstance(value, Decimal):
        return value
    if value in (None, "", False):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, ArithmeticError):  # pragma: no cover - defensive
        return Decimal("0")


def _get_plating_urls(recipe):
    """Return (image_url, placeholder_url) for ``recipe``."""

    recipe_id = None
    if recipe is not None:
        recipe_id = getattr(recipe, "pk", None) or getattr(recipe, "recipe_id", None)
    image_url = recipe_service.get_plating_image_url(recipe_id)
    placeholder_url = recipe_service.get_plating_placeholder_url()
    return image_url, placeholder_url


class RecipesListView(TemplateView):
    """Display all recipes with search and a refreshed table layout."""

    template_name = "inventory/recipes/list.html"

    def _render_table_partial(self):
        """Render the recipes table once so the list page has initial HTML."""

        table_view = RecipesTableView()
        table_view.setup(self.request, *self.args, **self.kwargs)
        table_context = table_view.get_context_data()
        table_html = render_to_string(
            table_view.get_template_names()[0],
            table_context,
            request=self.request,
        )
        return table_html, table_context

    def _build_page_context(self, form):
        table_html, table_ctx = self._render_table_partial()
        ctx = {
            "recipes_table": table_html,
            "form": form,
            "list_url": reverse("root"),
            "list_title": "Dashboard",
            "current_title": "Recipes",
        }
        ctx.update(table_ctx)
        if "recipe_count" not in ctx:
            page_obj = table_ctx.get("page_obj")
            ctx["recipe_count"] = (
                page_obj.paginator.count if page_obj and page_obj.paginator else 0
            )
        _, placeholder = _get_plating_urls(None)
        ctx.setdefault("plating_placeholder_url", placeholder)
        return ctx

    def get(self, request, *args, **kwargs):
        context = self._build_page_context(RecipeForm())
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = RecipeForm(request.POST)
        if form.is_valid():
            recipe = form.save()
            messages.success(request, "Recipe created", extra_tags="toast")
            return redirect("recipe_detail", pk=recipe.pk)
        context = self._build_page_context(form)
        return render(request, self.template_name, context)


class RecipesTableView(TemplateView):
    """Render the paginated table view of recipes for HTMX swaps."""

    template_name = "inventory/recipes/_recipes_table.html"

    def _get_queryset(self):
        qs, params = _filtered_recipes_queryset(self.request)
        self._filter_params = params
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self._get_queryset()
        page_obj, per_page = list_utils.paginate(self.request, qs)
        params = getattr(self, "_filter_params", {})
        ctx.update(params)
        try:
            querystring = list_utils.build_querystring(self.request)
        except Exception:  # pragma: no cover - defensive
            querystring = ""
        placeholder_url = recipe_service.get_plating_placeholder_url()
        recipes = list(page_obj.object_list)
        for recipe in recipes:
            rid = getattr(recipe, "pk", None)
            image_url = recipe_service.get_plating_image_url(rid)
            setattr(recipe, "plating_image_url", image_url)
            setattr(recipe, "plating_placeholder_url", placeholder_url)
        page_obj.object_list = recipes
        ctx.update(
            {
                "page_obj": page_obj,
                "page_size": per_page,
                "querystring": querystring,
                "recipes": recipes,
                "table_url": reverse("recipes_table"),
                "plating_placeholder_url": placeholder_url,
            }
        )
        if "recipe_count" not in ctx:
            ctx["recipe_count"] = qs.count()
        return ctx


def recipe_create(request):
    if request.method == "POST":
        form = RecipeForm(request.POST)
        formset = RecipeItemFormSet(request.POST, prefix="items")
        if form.is_valid() and formset.is_valid():
            data = form.cleaned_data
            items = []
            for f in formset.forms:
                if f.cleaned_data.get("DELETE"):
                    continue
                item_id = f.cleaned_data.get("item")
                if not item_id:
                    continue
                items.append(
                    {
                        "item_id": int(item_id.pk),
                        "quantity": float(f.cleaned_data.get("quantity") or 0),
                        "unit": f.cleaned_data.get("unit"),
                        "loss_pct": float(f.cleaned_data.get("loss_pct") or 0),
                    }
                )
            ok, msg, rid = recipe_service.create_recipe(data, items)
            if ok and rid:
                messages.success(request, "Recipe created", extra_tags="toast")
                return redirect("recipe_detail", pk=rid)
            messages.error(request, msg or "Error creating recipe", extra_tags="toast")
        # fallthrough on invalid
    else:
        form = RecipeForm()
        formset = RecipeItemFormSet(prefix="items")
    plating_image_url, plating_placeholder_url = _get_plating_urls(None)
    return render(
        request,
        "inventory/recipes/detail.html",
        {
            "form": form,
            "formset": formset,
            "recipe": None,
            "is_edit": False,
            "list_url": reverse("recipes_list"),
            "list_title": "Recipes",
            "current_title": "New Recipe",
            "plating_image_url": plating_image_url,
            "plating_placeholder_url": plating_placeholder_url,
        },
    )


def recipe_detail(request, pk: int):
    recipe = get_object_or_404(Recipe, pk=pk)
    if request.method == "POST":
        form = RecipeForm(request.POST, instance=recipe)
        formset = RecipeItemFormSet(request.POST, instance=recipe, prefix="items")
        if form.is_valid() and formset.is_valid():
            data = form.cleaned_data
            items = []
            for f in formset.forms:
                if f.cleaned_data.get("DELETE"):
                    continue
                item_id = f.cleaned_data.get("item")
                if not item_id:
                    continue
                items.append(
                    {
                        "item_id": int(item_id.pk),
                        "quantity": float(f.cleaned_data.get("quantity") or 0),
                        "unit": f.cleaned_data.get("unit"),
                        "loss_pct": float(f.cleaned_data.get("loss_pct") or 0),
                    }
                )
            ok, msg = recipe_service.update_recipe(recipe.pk, data, items)
            if ok:
                messages.success(request, "Recipe updated", extra_tags="toast")
                return redirect("recipe_detail", pk=recipe.pk)
            messages.error(request, msg or "Error updating recipe", extra_tags="toast")
        # fallthrough on invalid
    else:
        form = RecipeForm(instance=recipe)
        formset = RecipeItemFormSet(instance=recipe, prefix="items")
    plating_image_url, plating_placeholder_url = _get_plating_urls(recipe)
    setattr(recipe, "plating_image_url", plating_image_url)
    return render(
        request,
        "inventory/recipes/detail.html",
        {
            "form": form,
            "formset": formset,
            "recipe": recipe,
            "is_edit": True,
            "list_url": reverse("recipes_list"),
            "list_title": "Recipes",
            "current_title": recipe.name,
            "plating_image_url": plating_image_url,
            "plating_placeholder_url": plating_placeholder_url,
        },
    )


class RecipeCreatePartialView(View):
    """Drawer partial for creating a recipe with items."""

    template_name = "inventory/recipes/_form_partial.html"

    def get(self, request):
        form = RecipeForm()
        formset = RecipeItemFormSet(prefix="items")
        plating_image_url, plating_placeholder_url = _get_plating_urls(None)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "recipe": None,
                "is_edit": False,
                "plating_image_url": plating_image_url,
                "plating_placeholder_url": plating_placeholder_url,
            },
        )

    def post(self, request):
        form = RecipeForm(request.POST)
        formset = RecipeItemFormSet(request.POST, prefix="items")
        if form.is_valid() and formset.is_valid():
            data = form.cleaned_data
            items = []
            for f in formset.forms:
                if f.cleaned_data.get("DELETE"):
                    continue
                item_id = f.cleaned_data.get("item")
                if not item_id:
                    continue
                items.append(
                    {
                        "item_id": int(item_id.pk),
                        "quantity": float(f.cleaned_data.get("quantity") or 0),
                        "unit": f.cleaned_data.get("unit"),
                        "loss_pct": float(f.cleaned_data.get("loss_pct") or 0),
                    }
                )
            ok, msg, rid = recipe_service.create_recipe(data, items)
            if ok and rid:
                recipe = Recipe.objects.filter(pk=rid).first()
                recipe_payload = _serialize_recipe(recipe)
                return JsonResponse(
                    {
                        "ok": True,
                        "id": rid,
                        "message": "Recipe created",
                        "toast": True,
                        "toast_message": "Recipe created",
                        "toast_type": "success",
                        "close_only": True,
                        "recipe": recipe_payload,
                        "htmx": {
                            "event": "recipes:refresh",
                            "detail": {
                                "recipe": recipe_payload,
                                "action": "created",
                            },
                        },
                    }
                )
            return JsonResponse(
                {"ok": False, "message": msg or "Error creating recipe"}, status=400
            )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(_build_form_error_payload(form, formset), status=400)
        plating_image_url, plating_placeholder_url = _get_plating_urls(None)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "recipe": None,
                "is_edit": False,
                "plating_image_url": plating_image_url,
                "plating_placeholder_url": plating_placeholder_url,
            },
            status=400,
        )


class RecipeEditPartialView(View):
    """Drawer partial for editing a recipe with items."""

    template_name = "inventory/recipes/_form_partial.html"

    def get(self, request, pk: int):
        recipe = get_object_or_404(Recipe, pk=pk)
        form = RecipeForm(instance=recipe)
        formset = RecipeItemFormSet(instance=recipe, prefix="items")
        plating_image_url, plating_placeholder_url = _get_plating_urls(recipe)
        setattr(recipe, "plating_image_url", plating_image_url)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "recipe": recipe,
                "is_edit": True,
                "plating_image_url": plating_image_url,
                "plating_placeholder_url": plating_placeholder_url,
            },
        )

    def post(self, request, pk: int):
        recipe = get_object_or_404(Recipe, pk=pk)
        form = RecipeForm(request.POST, instance=recipe)
        formset = RecipeItemFormSet(request.POST, instance=recipe, prefix="items")
        if form.is_valid() and formset.is_valid():
            data = form.cleaned_data
            items = []
            for f in formset.forms:
                if f.cleaned_data.get("DELETE"):
                    continue
                item_id = f.cleaned_data.get("item")
                if not item_id:
                    continue
                items.append(
                    {
                        "item_id": int(item_id.pk),
                        "quantity": float(f.cleaned_data.get("quantity") or 0),
                        "unit": f.cleaned_data.get("unit"),
                        "loss_pct": float(f.cleaned_data.get("loss_pct") or 0),
                    }
                )
            ok, msg = recipe_service.update_recipe(recipe.pk, data, items)
            if ok:
                recipe.refresh_from_db()
                recipe_payload = _serialize_recipe(recipe)
                return JsonResponse(
                    {
                        "ok": True,
                        "id": recipe.pk,
                        "message": "Recipe updated",
                        "toast": True,
                        "toast_message": "Recipe updated",
                        "toast_type": "success",
                        "close_only": True,
                        "recipe": recipe_payload,
                        "htmx": {
                            "event": "recipes:refresh",
                            "detail": {
                                "recipe": recipe_payload,
                                "action": "updated",
                            },
                        },
                    }
                )
            return JsonResponse(
                {"ok": False, "message": msg or "Error updating recipe"}, status=400
            )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(_build_form_error_payload(form, formset), status=400)
        plating_image_url, plating_placeholder_url = _get_plating_urls(recipe)
        setattr(recipe, "plating_image_url", plating_image_url)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "recipe": recipe,
                "is_edit": True,
                "plating_image_url": plating_image_url,
                "plating_placeholder_url": plating_placeholder_url,
            },
            status=400,
        )


class RecipeViewPartialView(View):
    """Drawer partial for viewing a recipe with grouped items."""

    template_name = "inventory/recipes/_view_partial.html"

    def get(self, request, pk: int):
        recipe = get_object_or_404(
            Recipe.objects.prefetch_related(
                Prefetch(
                    "items",
                    queryset=RecipeItem.objects.select_related(
                        "item__category"
                    ).order_by("sort_order", "id"),
                )
            ),
            pk=pk,
        )

        items = []
        total_cost = Decimal("0.00")
        zero_cost = False

        for row in recipe.items.all():
            item = getattr(row, "item", None)
            qty = _to_decimal(getattr(row, "quantity", None))
            loss_pct = _to_decimal(getattr(row, "loss_pct", None))
            unit_label = getattr(row, "unit", "") or ""
            category = ""
            subcategory = ""
            base_unit_display = ""

            conversion = Decimal("1")
            last_price = Decimal("0")

            if item:
                category_obj = getattr(item, "category", None)
                category = getattr(category_obj, "category", "") or ""
                subcategory = getattr(category_obj, "sub_category", "") or ""
                unit_id = getattr(item, "unit_id", None)
                if unit_id:
                    try:
                        unit_info = UnitsService.get_unit_info(unit_id) or {}
                    except Exception:  # pragma: no cover - defensive
                        unit_info = {}
                    conversion = _to_decimal(unit_info.get("conversion_factor") or 1)
                    if not conversion:
                        conversion = Decimal("1")
                    base_unit_display = (
                        UnitsService.get_base_unit_display(unit_id) or ""
                    )
                last_price = _to_decimal(getattr(item, "last_purchase_price", None))
                if not last_price:
                    last_price = _to_decimal(
                        getattr(item, "initial_purchase_price", None)
                    )

            if not unit_label:
                unit_label = base_unit_display

            cost_per_base = Decimal("0")
            if conversion:
                try:
                    cost_per_base = last_price / conversion
                except ArithmeticError:  # pragma: no cover - defensive
                    cost_per_base = Decimal("0")

            cost_per_base = (
                cost_per_base.quantize(TWOPLACES) if cost_per_base else Decimal("0.00")
            )
            line_cost = (
                (cost_per_base * qty).quantize(TWOPLACES) if qty else Decimal("0.00")
            )
            has_zero_price = bool(qty and item and cost_per_base == Decimal("0.00"))
            zero_cost = zero_cost or has_zero_price
            total_cost += line_cost

            items.append(
                {
                    "id": row.pk,
                    "name": getattr(item, "name", "Unknown item"),
                    "quantity": qty,
                    "quantity_str": format(qty.normalize(), "f") if qty else "0",
                    "unit": unit_label,
                    "loss_pct": loss_pct,
                    "category": category or "Uncategorized",
                    "subcategory": subcategory,
                    "cost_per_base_unit": cost_per_base,
                    "cost_per_base_unit_str": format(cost_per_base, ".2f"),
                    "line_cost": line_cost,
                    "line_cost_str": format(line_cost, ".2f"),
                    "has_item": bool(item),
                    "has_zero_price": has_zero_price,
                }
            )

        total_cost = total_cost.quantize(TWOPLACES) if total_cost else Decimal("0.00")

        plating_image_url, plating_placeholder_url = _get_plating_urls(recipe)
        setattr(recipe, "plating_image_url", plating_image_url)
        return render(
            request,
            self.template_name,
            {
                "recipe": recipe,
                "items": items,
                "total_cost": total_cost,
                "zero_cost": zero_cost,
                "plating_image_url": plating_image_url,
                "plating_placeholder_url": plating_placeholder_url,
            },
        )
