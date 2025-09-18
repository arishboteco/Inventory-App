import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from inventory.models import Recipe


@pytest.mark.django_db
def test_recipe_list_table_renders_drawer_view_button(client):
    long_name = "Long Recipe " * 20
    recipe = Recipe.objects.create(name=long_name, is_active=True)

    resp = client.get(reverse("recipes_list"))

    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content, "html.parser")
    table = soup.select_one("#recipes-table")
    assert table is not None
    first_cell = table.select_one("tbody tr td")
    assert first_cell is not None
    assert long_name.strip() in first_cell.get_text()
    view_button = soup.select_one(
        'button[data-modal-type="drawer"][data-modal-url*="view/partial"]'
    )
    assert view_button is not None
    assert str(recipe.pk) in view_button.get("data-modal-url", "")
