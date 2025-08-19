# Combined Task List

This document consolidates the remediation tasks identified for resolving the Internal Server Error and improving project robustness.

## 1. Align requirements with service dependencies
- File: `requirements.txt`
- Ensure packages used by legacy services (e.g., `pandas`, `sqlalchemy`, `pyyaml`) are listed or refactor code to remove unused dependencies.

## 2. Provide safe defaults for critical environment variables
- File: `inventory_app/settings.py`
- Supply fallback values for `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` so the app can start without explicit environment variables.

## 3. Generalize database engine creation
- File: `inventory/views_ui.py`
- Modify `_get_item_engine` to construct an SQLAlchemy engine using the full database configuration, supporting both SQLite and Postgres.

