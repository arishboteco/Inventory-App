# Combined Task List

This document consolidates the remediation tasks identified for resolving the Internal Server Error and improving project robustness.

## 1. Remove Streamlit dependency from service modules
- Files: `legacy_streamlit/app/services/*.py`
- Wrap `streamlit` imports in `try/except` and provide a lightweight caching fallback when Streamlit is absent.

## 2. Align requirements with service dependencies
- File: `requirements.txt`
- Ensure packages used by legacy services (e.g., `pandas`, `sqlalchemy`, `pyyaml`) are listed or refactor code to remove unused dependencies.

## 3. Provide safe defaults for critical environment variables
- File: `inventory_app/settings.py`
- Supply fallback values for `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` so the app can start without explicit environment variables.

## 4. Generalize database engine creation
- File: `inventory/views_ui.py`
- Modify `_get_item_engine` to construct an SQLAlchemy engine using the full database configuration, supporting both SQLite and Postgres.

## 5. Document optional dependency behavior
- File: `legacy_streamlit/app/core/unit_inference.py`
- Clarify that YAML overrides are ignored if PyYAML isn't installed, and optionally log a warning to aid debugging.

