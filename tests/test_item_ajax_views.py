import json
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from inventory.views.items.stock import (
    CheckSimilarNamesView,
    PurchaseUnitsView,
    SubcategoriesView,
)


def test_purchase_units_view_returns_units():
    rf = RequestFactory()
    request = rf.get("/purchase-units/", {"base_unit": "kg"})
    with patch(
        "inventory.views.items.stock.get_purchase_unit_choices",
        return_value=[("kg", "kg")],
    ) as mock_method:
        response = PurchaseUnitsView.as_view()(request)
    assert response.status_code == 200
    assert json.loads(response.content) == {"purchase_units": [["kg", "kg"]]}
    mock_method.assert_called_with("kg")


def test_subcategories_view_returns_choices():
    rf = RequestFactory()
    request = rf.get("/subcategories/", {"category": "Food"})
    with patch(
        "inventory.views.items.stock.get_subcategory_choices",
        return_value=["Sweeteners"],
    ):
        response = SubcategoriesView.as_view()(request)
    assert response.status_code == 200
    assert json.loads(response.content) == {"subcategories": ["Sweeteners"]}


@pytest.mark.django_db
def test_check_similar_names_view(item_factory):
    item_factory(name="Sugar")
    rf = RequestFactory()
    request = rf.get("/items/check-similar/", {"name": "Sug"})
    response = CheckSimilarNamesView.as_view()(request)
    data = json.loads(response.content)
    assert response.status_code == 200
    assert data["has_similar"] is True
    assert any(it["name"] == "Sugar" for it in data["similar_items"])
