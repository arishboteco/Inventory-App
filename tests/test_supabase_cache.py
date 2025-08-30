import pytest

from inventory.services.supabase_cache import get_cached


def test_get_cached_raises_on_error():
    def fetch():
        raise ValueError("boom")

    cached = get_cached(fetch, ttl=1)
    with pytest.raises(ValueError):
        cached()
