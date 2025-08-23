import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from inventory.services import supabase_categories


class DummyResp:
    def __init__(self, data):
        self.data = data


class DummyClient:
    def table(self, name):
        assert name == "category"
        return self

    def select(self, fields):
        assert fields == "id,name,parent_id"
        return self

    def execute(self):
        return DummyResp([
            {"id": 1, "name": "Food", "parent_id": None},
            {"id": 2, "name": "Tools", "parent_id": None},
            {"id": 3, "name": "Fruit", "parent_id": 1},
            {"id": None, "name": "Bad", "parent_id": None},
            {"id": 4, "name": None, "parent_id": None},
        ])


def test_load_categories_from_supabase(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "url")
    monkeypatch.setenv("SUPABASE_KEY", "key")
    monkeypatch.setattr(
        supabase_categories, "create_client", lambda url, key: DummyClient()
    )
    cats = supabase_categories._load_categories_from_supabase()
    assert cats == {
        None: [{"id": 1, "name": "Food"}, {"id": 2, "name": "Tools"}],
        1: [{"id": 3, "name": "Fruit"}],
    }


def test_load_categories_supabase_exception(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "url")
    monkeypatch.setenv("SUPABASE_KEY", "key")

    class FailingClient(DummyClient):
        def table(self, name):
            raise supabase_categories.SupabaseException("fail")

    monkeypatch.setattr(
        supabase_categories, "create_client", lambda u, k: FailingClient()
    )
    cats = supabase_categories._load_categories_from_supabase()
    assert cats == {}


def test_get_categories_thread_safe(monkeypatch):
    monkeypatch.setattr(supabase_categories, "_cache", None)
    monkeypatch.setattr(supabase_categories, "_cache_time", None)

    def slow_load():
        time.sleep(0.01)
        return {None: [{"id": 1, "name": "Food"}]}

    monkeypatch.setattr(
        supabase_categories, "_load_categories_from_supabase", slow_load
    )

    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(lambda _: supabase_categories.get_categories(force=True), range(5)))

    assert supabase_categories._cache == {None: [{"id": 1, "name": "Food"}]}
