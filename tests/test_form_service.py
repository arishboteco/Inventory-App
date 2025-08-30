from unittest.mock import patch

import pytest
from django.db import DatabaseError

from inventory.services import form_service
from inventory.services.form_service import get_purchase_unit_choices


def test_get_purchase_unit_choices_returns_mapping():
    mapping = {"kg": ["kg", "g"]}
    with patch("inventory.services.form_service.get_units_map", return_value=mapping):
        assert get_purchase_unit_choices("kg") == [("kg", "kg"), ("g", "g")]


def test_get_purchase_unit_choices_defaults_to_base_unit():
    mapping = {"kg": ["kg", "g"]}
    with patch("inventory.services.form_service.get_units_map", return_value=mapping):
        assert get_purchase_unit_choices("box") == [("box", "box")]


def test_get_purchase_unit_choices_no_base_unit_returns_empty():
    assert get_purchase_unit_choices() == []


def test_get_department_choices_database_error(monkeypatch):
    def boom(*args, **kwargs):
        raise DatabaseError("boom")

    monkeypatch.setattr(form_service.Department.objects, "filter", boom)
    assert form_service.get_department_choices() == []


def test_get_department_choices_unexpected_exception(monkeypatch):
    def boom(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(form_service.Department.objects, "filter", boom)
    with pytest.raises(ValueError):
        form_service.get_department_choices()
