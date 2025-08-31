import types

import pytest

from inventory.models.category import Category
from inventory.models.unit import Unit
from inventory.services.categories_service import CategoriesService
from inventory.services.units_service import UnitsService


@pytest.mark.django_db
def test_get_unit_info_uses_orm(monkeypatch):
    """UnitsService should query the Unit model via the ORM."""

    UnitsService.get_unit_info.cache_clear()
    dummy_unit = types.SimpleNamespace(
        unit_id=1, base_unit="GM", purchase_unit="2 KG", conversion_factor=2000
    )
    called = {}

    def mock_get(unit_id):
        called["unit_id"] = unit_id
        return dummy_unit

    monkeypatch.setattr(Unit.objects, "get", mock_get)
    info = UnitsService.get_unit_info(1)

    assert called["unit_id"] == 1
    assert info == {
        "unit_id": 1,
        "base_unit": "GM",
        "purchase_unit": "2 KG",
        "conversion_factor": 2000.0,
    }


@pytest.mark.django_db
def test_get_category_info_uses_orm(monkeypatch):
    """CategoriesService should query the Category model via the ORM."""

    CategoriesService.get_category_info.cache_clear()
    dummy_category = types.SimpleNamespace(
        category_id=1, category="Grocery", sub_category="Juices And Purees"
    )
    called = {}

    def mock_get(category_id):
        called["category_id"] = category_id
        return dummy_category

    monkeypatch.setattr(Category.objects, "get", mock_get)
    info = CategoriesService.get_category_info(1)

    assert called["category_id"] == 1
    assert info == {
        "category_id": 1,
        "category": "Grocery",
        "sub_category": "Juices And Purees",
    }

