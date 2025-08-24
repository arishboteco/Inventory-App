import time
from concurrent.futures import ThreadPoolExecutor

from inventory.services import supabase_categories, supabase_client


class DummyResp:
    def __init__(self, data):
        self.data = data


class DummyClient:
    def table(self, name):
        assert name == "category"
        return self

    def select(self, fields):
        assert fields == "category_id,category,sub_category"
        return self

    def execute(self):
        return DummyResp(
            [
                {
                    "category_id": 1,
                    "category": "Food",
                    "sub_category": "Fruit",
                },
                {
                    "category_id": 2,
                    "category": "Food",
                    "sub_category": "Veg",
                },
                {
                    "category_id": 3,
                    "category": "Tools",
                    "sub_category": None,
                },
                {
                    "category_id": 4,
                    "category": "Food",
                    "sub_category": "Fruit",
                },
                {
                    "category_id": None,
                    "category": "Bad",
                    "sub_category": None,
                },
                {
                    "category_id": 5,
                    "category": None,
                    "sub_category": None,
                },
            ]
        )


def test_load_categories_from_supabase(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "url")
    monkeypatch.setenv("SUPABASE_KEY", "key")
    monkeypatch.setattr(supabase_client, "_client", None)
    monkeypatch.setattr(
        supabase_client, "create_client", lambda url, key: DummyClient()
    )
    cats = supabase_categories._load_categories_from_supabase()
    assert cats == {
        None: [{"id": 1, "name": "Food"}, {"id": 3, "name": "Tools"}],
        "Food": [{"id": 1, "name": "Fruit"}, {"id": 2, "name": "Veg"}],
    }


def test_load_categories_supabase_exception(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "url")
    monkeypatch.setenv("SUPABASE_KEY", "key")
    monkeypatch.setattr(supabase_client, "_client", None)

    class FailingClient(DummyClient):
        def table(self, name):
            raise supabase_categories.SupabaseException("fail")

    monkeypatch.setattr(
        supabase_client, "create_client", lambda u, k: FailingClient()
    )
    cats = supabase_categories._load_categories_from_supabase()
    assert cats == {}


def test_get_categories_thread_safe(monkeypatch):
    state = supabase_categories.get_categories._state
    state.value = None
    state.time = None

    def slow_load():
        time.sleep(0.01)
        return {None: [{"id": 1, "name": "Food"}]}

    monkeypatch.setattr(
        supabase_categories, "_load_categories_from_supabase", slow_load
    )

    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(lambda _: supabase_categories.get_categories(force=True), range(5)))

    assert state.value == {None: [{"id": 1, "name": "Food"}]}
