from unittest.mock import patch

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
