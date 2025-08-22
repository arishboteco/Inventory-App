import time
from concurrent.futures import ThreadPoolExecutor

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
    assert units == {"kg": ["kg", "g", "lb"], "ltr": ["ltr", "ml"]}


def test_load_units_supabase_exception(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "url")
    monkeypatch.setenv("SUPABASE_KEY", "key")

    class FailingClient(DummyClient):
        def table(self, name):
            raise supabase_units.SupabaseException("fail")

    monkeypatch.setattr(supabase_units, "create_client", lambda u, k: FailingClient())
    units = supabase_units._load_units_from_supabase()
    assert units == {}


def test_load_units_configuration_error(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "url")
    monkeypatch.setenv("SUPABASE_KEY", "key")

    def bad_client(url, key):
        raise RuntimeError("boom")

    monkeypatch.setattr(supabase_units, "create_client", bad_client)
    with pytest.raises(RuntimeError):
        supabase_units._load_units_from_supabase()


def test_get_units_thread_safe(monkeypatch):
    monkeypatch.setattr(supabase_units, "_cache", None)
    monkeypatch.setattr(supabase_units, "_cache_time", None)

    def slow_load():
        time.sleep(0.01)
        return {"kg": ["g"]}

    monkeypatch.setattr(supabase_units, "_load_units_from_supabase", slow_load)

    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(lambda _: supabase_units.get_units(force=True), range(5)))

    assert supabase_units._cache == {"kg": ["g"]}
