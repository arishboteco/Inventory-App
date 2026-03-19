# Copilot Instructions for Inventory-App

## What this app is

Django 5.2 app for restaurant inventory. PostgreSQL in prod; tests use SQLite in-memory. Tracks items, suppliers, stock movements, purchase orders/GRNs, recipes, and KPIs.

## Architecture you must follow

- Service layer in `inventory/services/` holds business logic. Views are thin HTTP adapters. Example: `services/form_service.py` provides dropdown/unit choices; `services/dashboard_service.py` computes KPIs; `services/stock_service.py` records stock movements; `services/item_service.py` handles item display/unit resolution.
- Models are modular in `inventory/models/` (`items.py`, `orders.py`, `recipes.py`, `departments.py`). Import via `from inventory.models import Item, Department, ...` (see `inventory/models/__init__.py`).
- Navigation is centralized in `inventory_app/navigation.py` and injected via the `primary_navigation` context processor. Top nav template lives at `templates/components/top_nav.html` and includes an inline desktop nav and grouped dropdown.

## Frontend conventions

- Tailwind/PostCSS build: entry `static/src/app.css` → output `static/css/app.css`. Build with `npm run build`; dev watch `npm run dev-css`.
- JS modules in `static/js/`: `top-nav.js` (accessible grouped menu), `modal.js`, `multiselect-chips.js` (enhanced multi-select), `predictive-dropdown.js`, `forms.js`, table helpers. The legacy `smart-navigation.js` was removed; don’t reference it.
- Desktop-first CSS with `max-*` responsive variants (e.g., `max-md:hidden`). Tokens in `static/src/tokens.css` feed `tailwind.config.js`.

## URLs and views

- Two routers:
  - API: `inventory/urls.py` (DRF endpoints)
  - UI: `inventory/ui_urls.py` (HTML pages). Common names: `items_list`, `purchase_orders_list`, `suppliers_list`, `history_reports`, etc. Root is `root` in `inventory_app/urls.py`.
- Item creation has two endpoints: `item_create` (HTMX post handler) and `item_create_partial` (small form for modal/drawer, template `templates/inventory/_item_create_partial.html`). Tests assert specific classes like `drawer-panel` and `max-w-drawer-xl` in that partial.

## Settings and environments

- Settings modules are under `inventory_app/settings/`: `base.py` (shared), `dev.py`, `staging.py`, `prod.py`/`production.py`, `test.py`.
- Templates dir is global `templates/`; context processors include `inventory_app.navigation.primary_navigation`.
- Static settings: files served by WhiteNoise; version string is `STATIC_VERSION` for cache-busting in templates.

## Dev workflows (use these exact commands)

- Install: `make install`
- CSS build (one-off): `npm run build`
- Dev loop (Django + CSS watcher): `make dev` (runs `scripts/dev.sh`)
- Run tests: `pytest` (pytest-django; test DB is SQLite in-memory). Note: `pytest.ini` adds `--reuse-db` and loads env from `env/test.example`.
- Lint/format: `make fmt && make lint`
- Optional: `python manage.py collectstatic --noinput` for packaging.

## Units system (critical domain rule)

- Items store only `unit_id`. Use `UnitsService` (see `UNITS_ARCHITECTURE.md`) to get display units and convert between base (recipe) and purchase units. Never hand-roll conversions or display `unit_id`.

## Testing expectations baked into templates

- Several tests parse HTML with BeautifulSoup. Keep IDs/classes stable:
  - Top nav exists on all pages (`templates/_base.html` includes `components/top_nav.html`).
  - The item create partial must render a root div with classes: `bg-white rounded-xl shadow border border-gray-200 overflow-hidden drawer-panel max-w-drawer-xl` and a departments multiselect container: `<div data-multiselect="chips" class="grid ...">`.
- Tests run fast: migrations for `inventory` are disabled in test settings; avoid Postgres-specific SQL in test paths.

## Common pitfalls in this repo

- Bypassing the service layer from views or templates.
- Forgetting to build CSS before relying on classes like `max-w-drawer-xl` (missing CSS makes visual checks fail). Use `npm run build`.
- Using removed files like `static/js/smart-navigation.js` or old settings module names. Use current settings in `inventory_app/settings/`.

## Quick file map to start editing

- Views: `inventory/views/...` (lists, detail, stock, etc.)
- Services: `inventory/services/...`
- Templates: `templates/inventory/*.html`, shared components under `templates/components/`
- Static JS/CSS: `static/js/*.js`, `static/src/app.css`
- Entry URLs: `inventory_app/urls.py`, includes API/UI routes

When adding features: put business logic in services, wire a thin view, render a template using shared components, and keep selectors/IDs compatible with tests.
