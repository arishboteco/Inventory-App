import pytest

from inventory.services import supabase_units


class DummyResp:
    def __init__(self, data):
        self.data = data


class DummyClient:
    def table(self, name):
        assert name == "units"
        return self

    def select(self, fields):
        # Ensure new schema columns are requested
        assert fields == "base_unit,purchase_unit"
        return self

    def execute(self):
        return DummyResp([
            {"base_unit": "kg", "purchase_unit": "g"},
            {"base_unit": "kg", "purchase_unit": "lb"},
            {"base_unit": "ltr", "purchase_unit": "ml"},
            {"base_unit": None, "purchase_unit": "x"},
            {"base_unit": "kg", "purchase_unit": None},
        ])


def test_load_units_from_supabase(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "url")
    monkeypatch.setenv("SUPABASE_KEY", "key")
    monkeypatch.setattr(supabase_units, "create_client", lambda url, key: DummyClient())

    units = supabase_units._load_units_from_supabase()
    assert units == {"kg": ["g", "lb"], "ltr": ["ml"]}
