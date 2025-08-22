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

## 4. Feature and UI Enhancements
- **Home Page**
  - Add login link and quick navigation buttons in `core/templates/core/home.html`.
  - Ensure login route exists and update navigation in `inventory_app/urls.py`.
- **Dashboard**
  - Extend `dashboard` view to compute totals (items, suppliers, transactions).
  - Update `core/templates/core/dashboard.html` with summary cards and chart placeholders.
  - Add tests in `tests/test_dashboard.py` for new context values.
- **Items**
  - Enable CSV export via new `ItemsExportView` and add export button.
  - Implement sortable table columns and add query parameters.
  - Add detail and delete views with corresponding templates and tests.
- **Suppliers**
  - Support CSV export and advanced filters in `SuppliersTableView` and template.
  - Replace GET toggle with POST form and confirmation dialog.
- **Indents**
  - Add search field to list views and include in HTMX requests.
  - Use POST forms for status updates with CSRF validation.
- **Purchase Orders**
  - Paginate and filter list view by status, supplier, and date range.
  - Add dynamic item rows to purchase order form with client-side validation.
- **Goods Received Notes (GRNs)**
  - Add supplier and date filters with pagination.
  - Link detail pages to originating purchase orders and provide export options.
- **Stock Movements**
  - Display recent stock transactions with pagination.
  - Provide sample CSV template and upload instructions.
- **History Reports**
  - Add sortable headers and totals row.
  - Enable asynchronous filtering using HTMX and partial templates.
- **Recipes**
  - Implement create/edit views with `RecipeForm` and `RecipeComponentFormSet`.
  - Persist added components in templates and views.
- **Login**
  - Style login form with Tailwind and add password reset link.
- **App-Wide Enhancements**
  - Enforce authentication and role-based permissions across views.
  - Abstract common search/export logic into reusable utilities and document usage.
