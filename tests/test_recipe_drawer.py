"""Tests for the recipe drawer partial views."""

from decimal import Decimal

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from inventory.models import Recipe, RecipeItem
from inventory.services.recipe_service import (
    get_plating_image_url,
    get_plating_placeholder_url,
)


@pytest.mark.django_db
def test_recipe_create_partial_invalid_ajax_returns_json(client):
    url = reverse("recipe_create_partial")
    data = {
        "name": "",
        "description_and_plating": "",
        "is_active": "on",
        "type": "",
        "default_yield_qty": "",
        "default_yield_unit": "",
        "items-TOTAL_FORMS": "1",
        "items-INITIAL_FORMS": "0",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "items-0-item": "",
        "items-0-quantity": "",
        "items-0-unit": "",
        "items-0-loss_pct": "",
        "items-0-DELETE": "",
    }

    response = client.post(
        url,
        data,
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["message"]
    assert "<" not in payload["message"]
    assert payload["errors"]["form"]["name"][0] == "This field is required."
    assert (
        payload["errors"]["formset"][0]["errors"]["item"][0]
        == "This field is required."
    )


@pytest.mark.django_db
def test_recipe_create_partial_invalid_non_ajax_returns_html(client):
    url = reverse("recipe_create_partial")
    data = {
        "name": "",
        "description_and_plating": "",
        "is_active": "on",
        "type": "",
        "default_yield_qty": "",
        "default_yield_unit": "",
        "items-TOTAL_FORMS": "1",
        "items-INITIAL_FORMS": "0",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "items-0-item": "",
        "items-0-quantity": "",
        "items-0-unit": "",
        "items-0-loss_pct": "",
        "items-0-DELETE": "",
    }

    response = client.post(url, data)

    assert response.status_code == 400
    assert response["Content-Type"].startswith("text/html")
    assert b"<form" in response.content


@pytest.mark.django_db
def test_recipe_edit_partial_invalid_ajax_returns_json(client, item_factory):
    item = item_factory(name="Flour")
    recipe = Recipe.objects.create(name="Bread", is_active=True)
    recipe_item = RecipeItem.objects.create(
        recipe=recipe,
        item=item,
        quantity=1,
        unit="kg",
        loss_pct=0,
    )

    url = reverse("recipe_edit_partial", args=[recipe.pk])
    data = {
        "name": "",
        "description_and_plating": (recipe.description or recipe.plating_notes or ""),
        "is_active": "on",
        "type": recipe.type or "",
        "default_yield_qty": recipe.default_yield_qty or "",
        "default_yield_unit": recipe.default_yield_unit or "",
        "items-TOTAL_FORMS": "1",
        "items-INITIAL_FORMS": "1",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "items-0-id": str(recipe_item.pk),
        "items-0-item": str(item.pk),
        "items-0-quantity": "1",
        "items-0-unit": recipe_item.unit or "",
        "items-0-loss_pct": "0",
        "items-0-DELETE": "",
    }

    response = client.post(
        url,
        data,
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["message"].startswith("Name:")
    assert "<" not in payload["message"]
    assert payload["errors"]["form"]["name"][0] == "This field is required."


@pytest.mark.django_db
def test_recipe_edit_partial_invalid_non_ajax_returns_html(client, item_factory):
    item = item_factory(name="Flour")
    recipe = Recipe.objects.create(name="Bread", is_active=True)
    recipe_item = RecipeItem.objects.create(
        recipe=recipe,
        item=item,
        quantity=1,
        unit="kg",
        loss_pct=0,
    )

    url = reverse("recipe_edit_partial", args=[recipe.pk])
    data = {
        "name": "",
        "description_and_plating": (recipe.description or recipe.plating_notes or ""),
        "is_active": "on",
        "type": recipe.type or "",
        "default_yield_qty": recipe.default_yield_qty or "",
        "default_yield_unit": recipe.default_yield_unit or "",
        "items-TOTAL_FORMS": "1",
        "items-INITIAL_FORMS": "1",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "items-0-id": str(recipe_item.pk),
        "items-0-item": str(item.pk),
        "items-0-quantity": "1",
        "items-0-unit": recipe_item.unit or "",
        "items-0-loss_pct": "0",
        "items-0-DELETE": "",
    }

    response = client.post(url, data)

    assert response.status_code == 400
    assert response["Content-Type"].startswith("text/html")
    assert b"<form" in response.content


@pytest.mark.django_db
def test_recipe_create_partial_success_returns_close_only_payload(client, item_factory):
    item = item_factory(name="Flour")
    url = reverse("recipe_create_partial")
    data = {
        "name": "Test Bread",
        "description_and_plating": "",
        "is_active": "on",
        "type": "",
        "default_yield_qty": "1",
        "default_yield_unit": "loaf",
        "items-TOTAL_FORMS": "1",
        "items-INITIAL_FORMS": "0",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "items-0-item": str(item.pk),
        "items-0-quantity": "2.5",
        "items-0-unit": "kg",
        "items-0-unit_display": "kg",
        "items-0-loss_pct": "0",
        "items-0-DELETE": "",
    }

    response = client.post(
        url,
        data,
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "redirect" not in payload
    assert payload.get("close_only") is True
    assert payload.get("reload") not in (True, "true")
    assert payload["recipe"]["name"] == "Test Bread"
    assert Recipe.objects.filter(name="Test Bread").exists()
    assert payload.get("htmx", {}).get("event") == "recipes:refresh"
    assert payload.get("htmx", {}).get("detail", {}).get("action") == "created"


@pytest.mark.django_db
def test_recipe_create_partial_drawer_header_has_thumbnail_and_toggle(client):
    response = client.get(reverse("recipe_create_partial"))

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    thumb = soup.select_one("[data-role='drawer-plating-image']")
    assert thumb is not None
    assert thumb["src"] == get_plating_placeholder_url()
    toggle = soup.select_one("[data-role='drawer-active-toggle'] input[type='checkbox']")
    assert toggle is not None
    notes = soup.find("textarea", {"name": "description_and_plating"})
    assert notes is not None


@pytest.mark.django_db
def test_recipe_edit_partial_drawer_header_prefills_thumbnail_and_notes(client):
    recipe = Recipe.objects.create(
        name="House Salad",
        description="Light and fresh",
        plating_notes="Serve chilled",
        is_active=False,
    )
    response = client.get(reverse("recipe_edit_partial", args=[recipe.pk]))

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    thumb = soup.select_one("[data-role='drawer-plating-image']")
    assert thumb is not None
    assert thumb["src"] == get_plating_image_url(recipe.pk)
    textarea = soup.find("textarea", {"name": "description_and_plating"})
    assert textarea is not None
    combined_text = "\n\n".join(
        part
        for part in [recipe.description.strip(), recipe.plating_notes.strip()]
        if part
    )
    assert textarea.text.strip() == combined_text.strip()
    toggle = soup.select_one("[data-role='drawer-active-toggle'] input[type='checkbox']")
    assert toggle is not None
    assert not toggle.has_attr("checked")


@pytest.mark.django_db
def test_recipes_table_includes_plating_thumbnail(client):
    recipe = Recipe.objects.create(name="Chocolate Tart", is_active=True)

    response = client.get(reverse("recipes_table"))

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    thumb = soup.select_one("[data-role='recipe-thumbnail']")
    assert thumb is not None
    assert thumb["src"] == get_plating_image_url(recipe.pk)
    assert get_plating_placeholder_url() in (thumb.get("onerror") or "")


@pytest.mark.django_db
def test_recipe_view_partial_renders_table_and_totals(client, item_factory):
    item = item_factory(name="Flour", initial_purchase_price=Decimal("6.00"))
    recipe = Recipe.objects.create(
        name="Bread", description="Classic loaf", is_active=True
    )
    RecipeItem.objects.create(
        recipe=recipe,
        item=item,
        quantity=Decimal("2"),
        unit="kg",
        loss_pct=Decimal("0"),
    )

    resp = client.get(reverse("recipe_view_partial", args=[recipe.pk]))

    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content, "html.parser")
    header = soup.find("h3")
    assert header and recipe.name in header.text
    plating_thumb = soup.select_one("[data-role='recipe-view-plating-image']")
    assert plating_thumb is not None
    assert plating_thumb["src"] == get_plating_image_url(recipe.pk)
    assert plating_thumb.get("onerror")
    first_row = soup.select_one("#items-table tbody tr")
    assert first_row and "Flour" in first_row.get_text()
    zero_notice = soup.select_one("#recipe-zero-cost-notice")
    assert zero_notice is not None
    assert "hidden" in zero_notice.get("class", [])


@pytest.mark.django_db
def test_recipe_view_partial_highlights_zero_cost_items(client, item_factory):
    item = item_factory(
        name="Free Garnish",
        last_purchase_price=Decimal("0"),
        initial_purchase_price=Decimal("0"),
    )
    recipe = Recipe.objects.create(name="Sample Dish", is_active=True)
    RecipeItem.objects.create(
        recipe=recipe,
        item=item,
        quantity=Decimal("1"),
        unit="pc",
        loss_pct=Decimal("0"),
    )

    resp = client.get(reverse("recipe_view_partial", args=[recipe.pk]))

    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content, "html.parser")
    zero_notice = soup.select_one("#recipe-zero-cost-notice")
    assert zero_notice is not None
    assert "hidden" not in zero_notice.get("class", [])
