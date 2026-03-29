from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_GET
from django.views.generic import DeleteView, TemplateView

from ..forms.recipe_forms import RecipeForm, RecipeItemEditFormSet, RecipeItemFormSet
from ..models import Indent, IndentItem, Recipe, RecipeItem
from ..services import list_utils, recipe_service
from ..services.units_service import UnitsService


def _filtered_recipes_queryset(request):
    """Return the recipe queryset filtered, searched and sorted for tables/cards."""

    qs = Recipe.objects.annotate(item_count=Count("items"))
    qs, params = list_utils.apply_filters_sort(
        request,
        qs,
        search_fields=["name", "description"],
        filter_fields={"active": "is_active", "type": "type"},
        allowed_sorts=["name", "type", "default_yield_unit", "is_active"],
        default_sort="name",
    )
    params.setdefault("q", "")
    params["recipe_count"] = qs.count()

    # Build filter options for the template filter_bar
    type_value = request.GET.get("type", "")
    params["filters"] = [
        {
            "name": "type",
            "label": "Type",
            "value": type_value,
            "options": [{"value": "", "label": "All Types"}]
            + [{"value": v, "label": label} for v, label in Recipe.Type.choices],
        },
    ]
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


def _normalize_unit_token(unit_raw: str) -> str:
    u = (unit_raw or "").strip().upper().replace(".", "")
    u = "".join(u.split())
    return u


def _recipe_yield_physical_amount(qty: Decimal, unit_raw: str) -> tuple[str, float]:
    """Dimension and amount in grams (mass), ml (volume), or count (each)."""

    q = float(qty or 1) or 1.0
    t = _normalize_unit_token(unit_raw)
    if t in ("KG", "KILO", "KILOS", "KILOGRAM", "KILOGRAMS"):
        return "mass", q * 1000.0
    if t in ("G", "GM", "GRAM", "GRAMS"):
        return "mass", q
    if t in ("L", "LITER", "LITRE", "LITERS", "LITRES"):
        return "volume", q * 1000.0
    if t in ("ML", "MILLILITER", "MILLILITERS", "MILLILITRE", "MILLILITRES"):
        return "volume", q
    return "count", q


def _unit_choices_for_dimension(dim: str) -> list[dict[str, str]]:
    if dim == "mass":
        return [
            {"code": "GM", "label": "g"},
            {"code": "KG", "label": "kg"},
        ]
    if dim == "volume":
        return [
            {"code": "ML", "label": "ml"},
            {"code": "L", "label": "L"},
        ]
    return [{"code": "PC", "label": "pc"}]


def _default_display_unit_code(unit_raw: str, dim: str) -> str:
    t = _normalize_unit_token(unit_raw)
    if dim == "mass":
        if t in ("KG", "KILO", "KILOS", "KILOGRAM", "KILOGRAMS"):
            return "KG"
        return "GM"
    if dim == "volume":
        if t in ("L", "LITER", "LITRE", "LITERS", "LITRES"):
            return "L"
        return "ML"
    return "PC"


def _sanitize_display_code(dim: str, code: str) -> str | None:
    c = (code or "").strip().upper()
    if dim == "mass":
        return c if c in ("GM", "KG") else None
    if dim == "volume":
        return c if c in ("ML", "L") else None
    return c if c == "PC" else None


def _cost_and_label_for_display(
    dim: str, cost_per_phys: float, display_code: str
) -> tuple[float, str]:
    """cost_per_phys is $ per g, per ml, or per count."""

    if dim == "mass":
        if display_code == "KG":
            return cost_per_phys * 1000.0, "kg"
        return cost_per_phys, "g"
    if dim == "volume":
        if display_code == "L":
            return cost_per_phys * 1000.0, "L"
        return cost_per_phys, "ml"
    return cost_per_phys, "pc"


def _collect_recipe_line_items(formset):
    """Build line-item dicts for recipe_service from a validated item formset."""

    items = []
    for f in formset.forms:
        if f.cleaned_data.get("DELETE"):
            continue
        item_obj = f.cleaned_data.get("item")
        sub_recipe_obj = f.cleaned_data.get("sub_recipe")
        if not item_obj and not sub_recipe_obj:
            continue
        items.append(
            {
                "item_id": int(item_obj.pk) if item_obj else None,
                "sub_recipe_id": (int(sub_recipe_obj.pk) if sub_recipe_obj else None),
                "quantity": float(f.cleaned_data.get("quantity") or 0),
                "unit": f.cleaned_data.get("unit"),
                "loss_pct": float(f.cleaned_data.get("loss_pct") or 0),
            }
        )
    return items


@require_GET
def recipe_meta(request, recipe_id: int):
    """JSON metadata for sub-recipe rows (cost per display unit, unit choices)."""

    recipe = get_object_or_404(Recipe, pk=recipe_id)
    total = recipe.get_total_cost()
    yield_qty = Decimal(str(recipe.default_yield_qty or 1)) or Decimal("1")
    yield_unit_raw = (recipe.default_yield_unit or "").strip()

    dim, phys_amt = _recipe_yield_physical_amount(yield_qty, yield_unit_raw)
    if phys_amt <= 0:
        phys_amt = 1.0
    try:
        cost_per_phys = float(total) / phys_amt
    except (ArithmeticError, ZeroDivisionError, ValueError, TypeError):
        cost_per_phys = 0.0

    unit_choices = _unit_choices_for_dimension(dim)
    default_code = _default_display_unit_code(yield_unit_raw, dim)
    req_code = (request.GET.get("display_unit") or "").strip().upper()
    display_code = _sanitize_display_code(dim, req_code) or default_code
    cost_per, unit_label = _cost_and_label_for_display(dim, cost_per_phys, display_code)

    return JsonResponse(
        {
            "ok": True,
            "recipe_id": recipe.recipe_id,
            "name": recipe.name,
            "base_unit": unit_label,
            "unit": unit_label,
            "cost_per_base_unit": cost_per,
            "category": "Sub-Recipe",
            "subcategory": "",
            "yield_dimension": dim,
            "unit_choices": unit_choices,
            "display_unit_code": display_code,
            "default_display_unit_code": default_code,
            "yield_qty": float(yield_qty),
            "yield_unit_raw": yield_unit_raw,
        }
    )


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
            items = _collect_recipe_line_items(formset)
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
        formset = RecipeItemEditFormSet(request.POST, instance=recipe, prefix="items")
        if form.is_valid() and formset.is_valid():
            data = form.cleaned_data
            items = _collect_recipe_line_items(formset)
            ok, msg = recipe_service.update_recipe(recipe.pk, data, items)
            if ok:
                messages.success(request, "Recipe updated", extra_tags="toast")
                return redirect("recipe_detail", pk=recipe.pk)
            messages.error(request, msg or "Error updating recipe", extra_tags="toast")
        # fallthrough on invalid
    else:
        form = RecipeForm(instance=recipe)
        formset = RecipeItemEditFormSet(instance=recipe, prefix="items")
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
            items = _collect_recipe_line_items(formset)
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
        formset = RecipeItemEditFormSet(instance=recipe, prefix="items")
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
        formset = RecipeItemEditFormSet(request.POST, instance=recipe, prefix="items")
        if form.is_valid() and formset.is_valid():
            data = form.cleaned_data
            items = _collect_recipe_line_items(formset)
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
                        "item__category", "sub_recipe"
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
            sub_recipe_obj = getattr(row, "sub_recipe", None)
            qty = _to_decimal(getattr(row, "quantity", None))
            loss_pct = _to_decimal(getattr(row, "loss_pct", None))
            unit_label = getattr(row, "unit", "") or ""
            category = ""
            subcategory = ""
            base_unit_display = ""

            if item:
                category_obj = getattr(item, "category", None)
                category = getattr(category_obj, "category", "") or ""
                subcategory = getattr(category_obj, "sub_category", "") or ""
                unit_id = getattr(item, "unit_id", None)
                if unit_id:
                    try:
                        base_unit_display = (
                            UnitsService.get_base_unit_display(unit_id) or ""
                        )
                    except Exception:  # pragma: no cover - defensive
                        base_unit_display = ""

            if not unit_label:
                unit_label = base_unit_display

            if item:
                cost_per_base = UnitsService.cost_per_base_for_item(item).quantize(
                    TWOPLACES
                )
            else:
                cost_per_base = Decimal("0.00")
            # Apply loss %: effective_qty = qty / (1 - loss_pct/100)
            effective_qty = qty
            if qty and loss_pct and loss_pct < 100:
                try:
                    effective_qty = qty / (1 - loss_pct / 100)
                except (ArithmeticError, ZeroDivisionError):
                    effective_qty = qty
            line_cost = (
                (cost_per_base * effective_qty).quantize(TWOPLACES)
                if effective_qty
                else Decimal("0.00")
            )
            # D1: For sub-recipe rows, compute cost from the sub-recipe
            if sub_recipe_obj and not item:
                try:
                    sub_cost = sub_recipe_obj.get_total_cost()
                    sub_yield = _to_decimal(
                        getattr(sub_recipe_obj, "default_yield_qty", None)
                    ) or Decimal("1")
                    cost_per_base = (
                        (sub_cost / sub_yield).quantize(TWOPLACES)
                        if sub_yield
                        else Decimal("0.00")
                    )
                except Exception:
                    cost_per_base = Decimal("0.00")
                loss_mult = Decimal("1") + (loss_pct / Decimal("100"))
                line_cost = (
                    (cost_per_base * qty * loss_mult).quantize(TWOPLACES)
                    if qty
                    else Decimal("0.00")
                )
                total_cost += line_cost
                items.append(
                    {
                        "id": row.pk,
                        "name": sub_recipe_obj.name,
                        "quantity": qty,
                        "quantity_str": format(qty.normalize(), "f") if qty else "0",
                        "unit": unit_label,
                        "loss_pct": loss_pct,
                        "category": "Sub-Recipe",
                        "subcategory": "",
                        "cost_per_base_unit": cost_per_base,
                        "cost_per_base_unit_str": format(cost_per_base, ".2f"),
                        "line_cost": line_cost,
                        "line_cost_str": format(line_cost, ".2f"),
                        "has_item": True,
                        "has_zero_price": False,
                        "is_sub_recipe": True,
                        "sub_recipe_id": sub_recipe_obj.pk,
                    }
                )
                continue

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
                    "is_sub_recipe": False,
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


def recipe_create_indent(request, pk: int):
    """Create a DRAFT indent from a recipe's ingredient list.

    POST params:
        yield_qty  – target yield quantity (defaults to recipe.default_yield_qty)
    """
    if request.method != "POST":
        return redirect("recipe_view_partial", pk=pk)

    recipe = get_object_or_404(
        Recipe.objects.prefetch_related(
            Prefetch("items", queryset=RecipeItem.objects.select_related("item"))
        ),
        pk=pk,
    )

    try:
        yield_qty = Decimal(
            str(request.POST.get("yield_qty") or recipe.default_yield_qty or 1)
        )
    except (ValueError, ArithmeticError):
        yield_qty = _to_decimal(recipe.default_yield_qty) or Decimal("1")

    base_yield = _to_decimal(recipe.default_yield_qty) or Decimal("1")
    scale = yield_qty / base_yield if base_yield else Decimal("1")

    ts = timezone.now().strftime("%Y%m%d%H%M%S%f")
    mrn = f"MRN-{ts}"

    indent = Indent.objects.create(
        mrn=mrn,
        notes=f"Recipe: {recipe.name}",
        status="DRAFT",
        date_required=None,
    )

    for row in recipe.items.all():
        item = getattr(row, "item", None)
        if not item:
            continue
        qty = _to_decimal(getattr(row, "quantity", None))
        loss_pct = _to_decimal(getattr(row, "loss_pct", None))
        effective_qty = qty * scale
        if loss_pct and loss_pct < 100:
            try:
                effective_qty = effective_qty / (1 - loss_pct / 100)
            except (ArithmeticError, ZeroDivisionError):
                pass
        effective_qty = effective_qty.quantize(TWOPLACES)
        IndentItem.objects.create(
            indent=indent,
            item=item,
            requested_qty=effective_qty,
        )

    messages.success(request, f"Indent {mrn} created from recipe", extra_tags="toast")
    return redirect("indent_detail", pk=indent.pk)


class RecipeDeleteView(LoginRequiredMixin, DeleteView):
    model = Recipe
    success_url = reverse_lazy("recipes_list")

    def get(self, request, *args, **kwargs):
        # No confirmation template — deletion is triggered via POST from the modal.
        return redirect("recipes_list")

    def post(self, request, *args, **kwargs):
        recipe = self.get_object()
        name = recipe.name
        recipe.delete()
        messages.success(request, f"Recipe '{name}' deleted.", extra_tags="toast")
        return redirect(self.success_url)


def food_cost_report(request):
    """Report listing all active FINAL recipes with food cost metrics."""
    status_filter = request.GET.get("status", "")
    qs = Recipe.objects.filter(type=Recipe.Type.FINAL, is_active=True).order_by("name")

    rows = []
    for recipe in qs:
        total_cost = recipe.get_total_cost()
        fcp = recipe.compute_food_cost_percentage(total_cost=total_cost)
        fc_status = recipe.compute_food_cost_status(food_cost_pct=fcp)
        if status_filter and fc_status != status_filter:
            continue
        selling = Decimal(str(recipe.selling_price or 0))
        gross_margin = (selling - total_cost) if selling else None
        rows.append(
            {
                "recipe": recipe,
                "total_cost": total_cost,
                "food_cost_pct": fcp,
                "fc_status": fc_status,
                "gross_margin": gross_margin,
            }
        )

    return render(
        request,
        "inventory/recipes/food_cost_report.html",
        {
            "rows": rows,
            "status_filter": status_filter,
            "list_url": "/recipes/",
            "list_title": "Recipes",
            "current_title": "Food Cost Report",
        },
    )
