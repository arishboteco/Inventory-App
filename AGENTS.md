# Inventory Pro — AGENTS.md

## Project Overview
Django 5.2 restaurant/cafe inventory management app. Tracks items, suppliers, stock movements, purchase orders/GRNs, recipes, KPIs, and food cost reporting. PostgreSQL in prod; SQLite in-memory for tests.

## Build / Lint / Test Commands

### Key commands (run from project root)
| Command | Purpose |
|---------|---------|
| `make ci` | Format + lint + test — **run before every commit** |
| `make fmt` | Format with Black |
| `make lint` | Lint with Ruff (auto-fix) |
| `make test` | Run pytest |
| `make coverage` | Tests with coverage report |
| `make precommit` | Run all pre-commit hooks |
| `npm test` | JavaScript tests (Jest) |
| `npm run build` | Build Tailwind CSS |
| `make dev` | Start Django + CSS watcher |

### Running a single test
```bash
pytest tests/test_specific_file.py              # Single file
pytest tests/test_specific_file.py::test_name   # Single test
pytest -k "keyword"                             # Tests matching keyword
pytest --reuse-db                               # Reuse test DB (default in pytest.ini)
```

### Dev server
```bash
make dev                                         # Django + CSS watcher
source .venv/bin/activate && python manage.py runserver 0.0.0.0:8000
```

## Code Style & Conventions

### Python
- **Version:** Python 3.13
- **Formatter:** Black (line-length 88)
- **Linter:** Ruff (extends E, F, W, I, E402; ignores E501 — handled by Black)
- **Import order:** isort with `profile = "black"`
- **Decimal arithmetic:** Always use `decimal.Decimal` for monetary/quantity values. Never `float`.
- **Template arithmetic:** Django templates cannot do Decimal math. Add `@property` on models instead.

### Imports
- Models: `from inventory.models import Item, Department, ...` (see `inventory/models/__init__.py`)
- Services: Business logic lives in `inventory/services/`. Views are thin HTTP adapters.
- Never bypass the service layer from views or templates.

### Naming Conventions
- **URL names:** `module_action` with underscores (e.g., `items_list`, `po_create_partial`)
- **Partial views:** Suffix with `_partial` (for HTMX drawers)
- **Branch names:** `feature/<short-slug>` targeting `feature/django-refactor`
- **PR titles:** `<verb>: <what changed>` (e.g., `fix: indent drawer submit`)

### Architecture Patterns
1. **Service layer:** All business logic in `inventory/services/`. Views are thin adapters.
2. **HTMX + Drawer pattern:** Create/edit forms load via HTMX into slide-in drawers. Drawer forms must use `fetch()` or `hx-post` — **never** native `form.submit()`.
3. **JSON responses:** AJAX-serving views return `JsonResponse({'ok': True, 'id': obj.pk})`.
4. **Formsets:** PO line items and recipe ingredients use Django formsets. Always include the management form.
5. **Navigation:** Driven from `inventory_app/navigation.py`. Not hardcoded in templates.

### Error Handling
- Views should catch exceptions and return appropriate JSON or render error templates.
- Model `save()` methods include safety nets (e.g., `line_total` computation on PurchaseOrderItem).
- Use `F()` expressions for atomic updates (e.g., `Item.current_stock`).

### Frontend
- **CSS:** Tailwind CSS utility classes. Build: `npm run build`. Watch: `npm run dev-css`.
- **JS modules:** `static/js/` — `top-nav.js`, `modal.js`, `multiselect-chips.js`, `predictive-dropdown.js`, `forms.js`.
- **Desktop-first** CSS with `max-*` responsive variants (e.g., `max-md:hidden`).
- **HTML comments:** Use `<!-- -->` not `{# #}` — Django comments can leak in partials.

## Database & Migrations

### Critical: PostgreSQL DDL in migrations
Several inventory migrations (0004, 0007, 0030, 0032, 0033) contain raw PostgreSQL DDL (`DO $$`, `CREATE EXTENSION`, `ADD COLUMN IF NOT EXISTS`). These **fail on SQLite**.

**Local SQLite dev workflow:**
1. Apply non-inventory migrations: `python manage.py migrate admin auth contenttypes sessions django_q`
2. Fake inventory migrations: `python manage.py migrate --fake inventory`
3. Create tables from ORM models using `schema_editor.create_model()`

Test settings (`inventory_app.settings.test`) set `MIGRATION_MODULES = {"inventory": None}` and use `:memory:` SQLite.

### Environment variables (minimum `.env`)
```
DJANGO_SECRET_KEY=<random-string>
DATABASE_URL=sqlite:///db.sqlite3
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DISABLE_KEEP_ALIVE=true
DJANGO_SETTINGS_MODULE=inventory_app.settings.dev
```

## Domain Rules

### Units system
Items store only `unit_id`. Use `UnitsService` to get display units and convert between base (recipe) and purchase units. **Never** hand-roll conversions or display `unit_id` directly.

### PurchaseOrderItem.line_total
Has a NOT NULL constraint. Must always be `quantity_ordered × unit_price` before saving.

### Status flows
- **Indent:** `SUBMITTED → APPROVED → PROCESSING → COMPLETED` (or `CANCELLED`)
- **PO:** `DRAFT → SENT → RECEIVED`
- **GRN:** `DRAFT → RECEIVED`
- **Stock Take:** `DRAFT → IN_PROGRESS → COMPLETED`

### StockTransaction types
`RECEIVING`, `ADJUSTMENT`, `WASTAGE`, `TRANSFER`, `SALE`, `ISSUE`

## Testing
- **Framework:** pytest-django with SQLite in-memory DB
- **Config:** `pytest.ini` sets `DJANGO_SETTINGS_MODULE = inventory_app.settings.test`
- **JS tests:** Jest in `tests/js/`, run with `npm test`
- **HTML parsing:** Several tests use BeautifulSoup. Keep IDs/classes stable.
- **Note:** 28 of ~189 Python tests have pre-existing failures (stale assertions, removed imports). 161+ pass.

## Common Pitfalls
1. Bypassing the service layer from views/templates
2. Forgetting to build CSS before using custom classes (e.g., `max-w-drawer-xl`)
3. Using native `form.submit()` in drawers — causes full-page navigation to partial URLs
4. Forgetting `line_total` computation before saving PO items
5. Attempting Decimal math in templates — use model `@property` instead
6. Referencing removed files (`smart-navigation.js`, old settings modules)

## Quick File Map
| Area | Location |
|------|----------|
| Views | `inventory/views/` |
| Services | `inventory/services/` |
| Models | `inventory/models/` (modular: `items.py`, `orders.py`, `recipes.py`, etc.) |
| Templates | `templates/inventory/`, shared: `templates/components/` |
| Static JS | `static/js/` |
| Static CSS | `static/src/app.css` → `static/css/app.css` |
| URLs | `inventory_app/urls.py` (entry), `inventory/urls.py` (API), `inventory/ui_urls.py` (HTML) |
| Navigation | `inventory_app/navigation.py` |
| Settings | `inventory_app/settings/` (`base.py`, `dev.py`, `test.py`, `prod.py`) |
