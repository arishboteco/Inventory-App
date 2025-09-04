import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from inventory.models import Recipe


@pytest.mark.django_db
def test_recipe_card_handles_long_text_without_overlap(client):
    long_name = "Long Recipe " * 20
    recipe = Recipe.objects.create(name=long_name)
    resp = client.get(reverse("recipes_list"))
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content, "html.parser")
    card = soup.find("a", href=reverse("recipe_detail", args=[recipe.pk]))
    wrapper = card.find("div", class_="flex")
    assert wrapper is not None
    classes = wrapper.get("class", [])
    assert "overflow-hidden" in classes
    assert "gap-4" in classes
    img = wrapper.find("img")
    img_classes = img.get("class", [])
    for expected in ["max-w-full", "h-auto", "object-contain"]:
        assert expected in img_classes
