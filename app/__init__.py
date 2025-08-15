"""Compatibility package mapping to legacy_streamlit.app.* modules."""
from importlib import import_module
import sys

for _pkg in ("core", "services", "ui", "db", "config"):
    module = import_module(f"legacy_streamlit.app.{_pkg}")
    sys.modules[f"{__name__}.{_pkg}"] = module
