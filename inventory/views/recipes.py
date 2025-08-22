from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView

from ..forms.recipe_forms import RecipeForm, RecipeComponentFormSet
from ..models import Recipe


class RecipesListView(TemplateView):
    template_name = "inventory/recipes/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["recipes"] = Recipe.objects.all().order_by("name")
        return ctx


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
