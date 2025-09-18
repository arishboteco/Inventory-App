"""Tests for the recipe drawer create/edit partial views."""

import pytest
from django.urls import reverse

from inventory.models import Recipe, RecipeItem


@pytest.mark.django_db
def test_recipe_create_partial_invalid_ajax_returns_json(client):
    url = reverse("recipe_create_partial")
    data = {
        "name": "",
        "description": "",
        "is_active": "on",
        "type": "",
        "default_yield_qty": "",
        "default_yield_unit": "",
        "plating_notes": "",
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
    assert payload["errors"]["formset"][0]["errors"]["item"][0] == "This field is required."


@pytest.mark.django_db
def test_recipe_create_partial_invalid_non_ajax_returns_html(client):
    url = reverse("recipe_create_partial")
    data = {
        "name": "",
        "description": "",
        "is_active": "on",
        "type": "",
        "default_yield_qty": "",
        "default_yield_unit": "",
        "plating_notes": "",
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
        "description": recipe.description or "",
        "is_active": "on",
        "type": recipe.type or "",
        "default_yield_qty": recipe.default_yield_qty or "",
        "default_yield_unit": recipe.default_yield_unit or "",
        "plating_notes": recipe.plating_notes or "",
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
        "description": recipe.description or "",
        "is_active": "on",
        "type": recipe.type or "",
        "default_yield_qty": recipe.default_yield_qty or "",
        "default_yield_unit": recipe.default_yield_unit or "",
        "plating_notes": recipe.plating_notes or "",
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
