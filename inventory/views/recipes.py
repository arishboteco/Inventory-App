from django.shortcuts import get_object_or_404, render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import TemplateView

from ..models import Recipe, RecipeComponent


class RecipesListView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/recipes/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["recipes"] = Recipe.objects.all().order_by("name")
        return ctx


class RecipeDetailView(LoginRequiredMixin, View):
    template_name = "inventory/recipes/detail.html"

    def get(self, request, pk: int):
        recipe = get_object_or_404(Recipe, pk=pk)
        components = RecipeComponent.objects.filter(parent_recipe=recipe).order_by(
            "sort_order", "id"
        )
        return render(
            request,
            self.template_name,
            {"recipe": recipe, "components": components},
        )


class RecipeComponentRowView(LoginRequiredMixin, View):
    template_name = "inventory/recipes/_component_row.html"

    def get(self, request, pk: int):
        recipe = get_object_or_404(Recipe, pk=pk)
        index = int(request.GET.get("index", 0))
        return render(
            request,
            self.template_name,
            {"recipe": recipe, "index": index, "comp": None},
        )
