from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.generic import TemplateView

from ..forms.recipe_forms import RecipeForm, RecipeComponentFormSet
from ..models import Recipe


class RecipesListView(TemplateView):
    """Display all recipes with search and card grid.

    Template: inventory/recipes/list.html.
    """

    template_name = "inventory/recipes/list.html"
    grid_template = "inventory/recipes/_recipes_cards.html"

    def _get_recipes(self):
        """Return recipes annotated with component counts and optional images."""
        q = (self.request.GET.get("q") or "").strip()
        qs = Recipe.objects.all().annotate(component_count=Count("components")).order_by("name")
        if q:
            qs = qs.filter(name__icontains=q)

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
                    "component_count": r.component_count,
                }
            )
        return recipes, q

    def get(self, request, *args, **kwargs):
        recipes, q = self._get_recipes()
        if request.headers.get("HX-Request"):
            return render(request, self.grid_template, {"recipes": recipes})

        grid_html = render_to_string(self.grid_template, {"recipes": recipes}, request=request)
        ctx = {"recipes_grid": grid_html, "q": q}
        return render(request, self.template_name, ctx)


def recipe_create(request):
    if request.method == "POST":
        form = RecipeForm(request.POST)
        formset = RecipeComponentFormSet(request.POST, prefix="components")
        if form.is_valid() and formset.is_valid():
            recipe = form.save()
            formset.instance = recipe
            formset.save()
            messages.success(request, "Recipe created")
            return redirect("recipe_detail", pk=recipe.pk)
    else:
        form = RecipeForm()
        formset = RecipeComponentFormSet(prefix="components")
    return render(
        request,
        "inventory/recipes/detail.html",
        {"form": form, "formset": formset, "recipe": None, "is_edit": False},
    )


def recipe_detail(request, pk: int):
    recipe = get_object_or_404(Recipe, pk=pk)
    if request.method == "POST":
        form = RecipeForm(request.POST, instance=recipe)
        formset = RecipeComponentFormSet(
            request.POST, instance=recipe, prefix="components"
        )
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "Recipe updated")
            return redirect("recipe_detail", pk=recipe.pk)
    else:
        form = RecipeForm(instance=recipe)
        formset = RecipeComponentFormSet(instance=recipe, prefix="components")
    return render(
        request,
        "inventory/recipes/detail.html",
        {"form": form, "formset": formset, "recipe": recipe, "is_edit": True},
    )
