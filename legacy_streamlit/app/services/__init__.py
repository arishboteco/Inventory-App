try:
    import streamlit as st
    cache_data = st.cache_data
except Exception:  # pragma: no cover - Streamlit not installed
    from functools import lru_cache

    def cache_data(func=None, **_kwargs):
        def decorator(f):
            cached = lru_cache(maxsize=None)(f)
            cached.clear = cached.cache_clear
            return cached

        if func is None:
            return decorator
        return decorator(func)

__all__ = ["cache_data"]

