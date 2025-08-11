import pytest

from app.core.unit_inference import infer_units


def test_infer_units_from_name_milk():
    base, purchase = infer_units("Whole Milk", None)
    assert base == "ltr"
    assert purchase == "carton"


def test_infer_units_from_category_produce():
    base, purchase = infer_units("Mystery Veg", "Produce")
    assert base == "kg"
    assert purchase is None


def test_infer_units_default_fallback():
    base, purchase = infer_units("Widget", None)
    assert base == "pcs"
    assert purchase is None
