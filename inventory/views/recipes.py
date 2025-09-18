from django.contrib import messages
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from ..forms.recipe_forms import RecipeItemFormSet, RecipeForm
from ..models import Recipe
from ..services import list_utils, recipe_service


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


class RecipesListView(TemplateView):
    """Display all recipes with search and card grid.

    Template: inventory/recipes/list.html.
    """

    template_name = "inventory/recipes/list.html"
    grid_template = "inventory/recipes/_recipes_cards.html"

    def _get_recipes(self):
        """Return recipes annotated with item counts and optional images."""

        qs, params = _filtered_recipes_queryset(self.request)

        recipes = []
        for r in qs:
            image = (
                getattr(r, "image", None)
                or getattr(r, "image_url", None)
                or "https://via.placeholder.com/400x300?text=Recipe"
            )
            recipes.append(
                {
                    "recipe_id": r.recipe_id,
                    "name": r.name,
                    "image": image,
                    "item_count": r.item_count,
                    "component_count": r.item_count,
                    "category": getattr(r, "type", "") or "",
                    "default_yield_unit": getattr(r, "default_yield_unit", "") or "",
                    "is_active": r.is_active,
                }
            )
        return recipes, params

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

    def get(self, request, *args, **kwargs):
        recipes, params = self._get_recipes()
        if request.headers.get("HX-Request"):
            return render(request, self.grid_template, {"recipes": recipes})

        table_html, table_ctx = self._render_table_partial()
        grid_html = render_to_string(
            self.grid_template, {"recipes": recipes}, request=request
        )
        ctx = {
            "recipes_grid": grid_html,
            "recipes_table": table_html,
            "recipe_count": params.get("recipe_count", len(recipes)),
            "form": RecipeForm(),
            "list_url": reverse("root"),
            "list_title": "Dashboard",
            "current_title": "Recipes",
        }
        ctx.update(params)
        ctx.update(
            {
                "page_size": table_ctx.get("page_size"),
                "sort": table_ctx.get("sort"),
                "direction": table_ctx.get("direction"),
                "querystring": table_ctx.get("querystring"),
            }
        )
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        form = RecipeForm(request.POST)
        if form.is_valid():
            recipe = form.save()
            messages.success(request, "Recipe created", extra_tags="toast")
            return redirect("recipe_detail", pk=recipe.pk)

        recipes, params = self._get_recipes()
        table_html, table_ctx = self._render_table_partial()
        grid_html = render_to_string(
            self.grid_template, {"recipes": recipes}, request=request
        )
        ctx = {
            "recipes_grid": grid_html,
            "recipes_table": table_html,
            "recipe_count": params.get("recipe_count", len(recipes)),
            "form": form,
            "list_url": reverse("root"),
            "list_title": "Dashboard",
            "current_title": "Recipes",
        }
        ctx.update(params)
        ctx.update(
            {
                "page_size": table_ctx.get("page_size"),
                "sort": table_ctx.get("sort"),
                "direction": table_ctx.get("direction"),
                "querystring": table_ctx.get("querystring"),
            }
        )
        return render(request, self.template_name, ctx)


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
        ctx.update(
            {
                "page_obj": page_obj,
                "page_size": per_page,
                "querystring": querystring,
                "recipes": page_obj.object_list,
                "table_url": reverse("recipes_table"),
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
        },
    )


def recipe_detail(request, pk: int):
    recipe = get_object_or_404(Recipe, pk=pk)
    if request.method == "POST":
        form = RecipeForm(request.POST, instance=recipe)
        formset = RecipeItemFormSet(
            request.POST, instance=recipe, prefix="items"
        )
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
        },
    )


class RecipeCreatePartialView(View):
    """Drawer partial for creating a recipe with items."""

    template_name = "inventory/recipes/_form_partial.html"

    def get(self, request):
        form = RecipeForm()
        formset = RecipeItemFormSet(prefix="items")
        return render(
            request,
            self.template_name,
            {"form": form, "formset": formset, "recipe": None, "is_edit": False},
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
                return JsonResponse(
                    {
                        "ok": True,
                        "id": rid,
                        "message": "Recipe created",
                        "redirect": reverse("recipe_detail", kwargs={"pk": rid}),
                        "toast": True,
                    }
                )
            return JsonResponse({"ok": False, "message": msg or "Error creating recipe"}, status=400)
        return render(
            request,
            self.template_name,
            {"form": form, "formset": formset, "recipe": None, "is_edit": False},
            status=400,
        )


class RecipeEditPartialView(View):
    """Drawer partial for editing a recipe with items."""

    template_name = "inventory/recipes/_form_partial.html"

    def get(self, request, pk: int):
        recipe = get_object_or_404(Recipe, pk=pk)
        form = RecipeForm(instance=recipe)
        formset = RecipeItemFormSet(instance=recipe, prefix="items")
        return render(
            request,
            self.template_name,
            {"form": form, "formset": formset, "recipe": recipe, "is_edit": True},
        )

    def post(self, request, pk: int):
        recipe = get_object_or_404(Recipe, pk=pk)
        form = RecipeForm(request.POST, instance=recipe)
        formset = RecipeItemFormSet(
            request.POST, instance=recipe, prefix="items"
        )
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
                return JsonResponse(
                    {
                        "ok": True,
                        "id": recipe.pk,
                        "message": "Recipe updated",
                        "redirect": reverse("recipe_detail", kwargs={"pk": recipe.pk}),
                        "toast": True,
                    }
                )
            return JsonResponse({"ok": False, "message": msg or "Error updating recipe"}, status=400)
        return render(
            request,
            self.template_name,
            {"form": form, "formset": formset, "recipe": recipe, "is_edit": True},
            status=400,
        )
