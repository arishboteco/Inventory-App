# Inventory Pro — Developer Guide

Quick reference for anyone working on this codebase.

---

## Documentation Index

| File | Contents |
|------|----------|
| [docs/workflow.md](docs/workflow.md) | Indent → PO → GRN → Stock flow with mermaid diagram |
| [docs/architecture.md](docs/architecture.md) | Category and Units schema reference |
| [docs/design-system.md](docs/design-system.md) | Tailwind design tokens, colour palette, WCAG contrast ratios |
| [docs/styleguide.md](docs/styleguide.md) | Tailwind patterns, component styles, dark mode notes |
| [docs/component-guide.md](docs/component-guide.md) | Reusable template component reference |
| [docs/user-journeys.md](docs/user-journeys.md) | Personas, key flows, Figma prototype link |
| [docs/development-workflow.md](docs/development-workflow.md) | Changelog discipline and daily dev workflow |
| [docs/deployment.md](docs/deployment.md) | Render deployment setup guide |
| [docs/deployment-env-setup.md](docs/deployment-env-setup.md) | Render environment variable reference |
| [docs/deployment-troubleshooting.md](docs/deployment-troubleshooting.md) | Render troubleshooting (threading, superuser, etc.) |
| [docs/security.md](docs/security.md) | Secrets management — never commit credentials |

---

## 1. What This App Does

F&B inventory management for restaurants/cafés. The core workflow:

```
Indent (request) → Purchase Order → GRN (goods received) → Stock Movement
```

Plus: Recipe costing, Supplier management, Stock takes, ML demand forecasting.

**Live:** https://inventory-app-kguo.onrender.com/ (admin / admin123!)
**Hosting:** Render.com free tier (cold starts ~50s after 15min idle)

---

## 2. Directory Structure

```
Inventory-App/
├── inventory/              # Main Django app — all business logic
│   ├── models/             # Data layer (12 files)
│   ├── views/              # HTTP handlers (13 files + items/ submodule)
│   ├── forms/              # Django forms and formsets (11 files)
│   ├── services/           # Business logic layer (25 files)
│   ├── migrations/         # DB schema history (32 files)
│   ├── middleware/         # LazyStockSnapshotMiddleware
│   ├── templatetags/       # icon_tags, category_tags, form_tags
│   ├── utils/              # category_migration
│   ├── management/commands/# Custom manage.py commands (11 files)
│   ├── serializers.py      # DRF serializers
│   ├── admin.py            # Minimal admin registration
│   ├── ui_urls.py          # 85 HTML UI routes
│   └── urls.py             # DRF API routes
│
├── core/                   # Auth, middleware, config
│   ├── config.py           # Env var loading (dataclass)
│   ├── middleware.py        # LoginRequiredMiddleware
│   ├── error_logging_middleware.py  # 500 error detail logger
│   ├── performance_middleware.py    # Query/response time tracker
│   ├── views.py            # Dashboard, health check, password reset
│   └── viewmodels.py       # Pydantic view models
│
├── inventory_app/          # Django project config
│   ├── settings/
│   │   ├── base.py         # Shared settings
│   │   ├── dev.py          # Local development
│   │   └── prod.py         # Production (Render)
│   ├── urls.py             # Root URL dispatcher
│   ├── wsgi.py
│   └── asgi.py
│
├── templates/              # All HTML templates (372 files)
│   ├── _base.html          # Master layout
│   ├── components/         # 35 reusable UI components
│   ├── inventory/          # Feature templates (~150 files)
│   ├── registration/       # Login, password reset
│   └── guides/             # In-app user guide
│
├── static/
│   ├── js/                 # ~30 JS files (vanilla + HTMX)
│   ├── src/app.css         # Tailwind CSS source
│   └── img/                # SVG icons/images
│
├── tests/                  # 60+ test files
├── docs/                   # Architecture docs, guides
│   └── archive/            # Historical analysis docs (for reference only)
│
├── build.sh                # Render build script
├── render.yaml             # Render deployment config
├── Makefile                # Dev commands (fmt, lint, test, ci)
├── CLAUDE.md               # AI assistant instructions
└── DEVELOPER_GUIDE.md      # This file
```

---

## 3. Key Models

```
Item                        — inventory item (stock, reorder point, ABC class)
  └── StockTransaction      — every stock movement (RECEIVING/ADJUSTMENT/WASTAGE/TRANSFER)
  └── StockSnapshot         — daily stock level snapshot

Supplier                    — vendor details

Indent                      — internal purchase request
  └── IndentItem

PurchaseOrder               — order sent to supplier
  └── PurchaseOrderItem     — line_total = quantity_ordered × unit_price (NOT NULL)

GoodsReceivedNote           — goods arrival confirmation
  └── GRNItem

Recipe (FINAL or SUB)       — dish or sub-component with selling_price, target_food_cost_pct
  └── RecipeItem            — ingredient: either item_id OR sub_recipe_id (not both)

StockTake                   — physical count session
  └── StockTakeItem

Department                  — kitchen/bar/pastry etc.
Category / SubCategory / Unit — reference data
```

**Critical constraints:**
- `PurchaseOrderItem.line_total` has NOT NULL — always set before save
- `RecipeItem.item_id` is nullable (sub-recipe rows have no item)
- `RecipeItem` must have exactly one of `item` or `sub_recipe`

---

## 4. Status Flows

| Model | States |
|-------|--------|
| Indent | SUBMITTED → APPROVED → PROCESSING → COMPLETED (or CANCELLED) |
| PurchaseOrder | DRAFT → SENT → RECEIVED |
| GRN | DRAFT → RECEIVED (confirming auto-fulfills linked indents) |
| StockTake | DRAFT → IN_PROGRESS → COMPLETED |

---

## 5. Architecture Patterns

### HTMX Drawer Pattern
Most create/edit forms use a slide-in drawer loaded via HTMX:

```html
<!-- Trigger button -->
<button data-modal-url="/items/create/partial/" data-modal-type="drawer">
  Add Item
</button>
```

A delegated JS handler in `modal.js` intercepts clicks, fetches the partial HTML, and injects it into the drawer container.

**Rule:** Drawer forms must submit via `fetch()` or `hx-post` — never native `form.submit()`, which causes full-page navigation to the raw partial URL.

### JSON Response Convention
Views serving drawers return JSON for AJAX requests:

```python
if request.headers.get("X-Requested-With") == "XMLHttpRequest":
    return JsonResponse({"ok": True, "id": obj.pk})
```

### Formsets (PO items, Recipe ingredients)
Django formsets manage inline rows. Always include the management form:

```html
{{ formset.management_form }}
{% for form in formset %}
  <!-- row -->
{% endfor %}
```

Management field names follow the pattern: `items-TOTAL_FORMS`, `items-0-item`, etc.

### Service Layer
Views should be thin. Business logic lives in `inventory/services/`:

```python
# In a view
from inventory.services.item_service import get_low_stock_items

items = get_low_stock_items(threshold=10)
```

Never put complex queries or calculations directly in views.

---

## 6. Views Reference

| File | Lines | Covers |
|------|-------|--------|
| `views/indents.py` | 1,201 | List, detail, create/edit, consolidation, PDF, issue tracking |
| `views/purchase_orders.py` | 856 | PO list, detail, create, receive |
| `views/recipes.py` | 779 | Recipe CRUD, food cost report, sub-recipe costing |
| `views/stock.py` | 702 | Movements, history, adjustments, wastage, transfers |
| `views/goods_received.py` | 567 | GRN create, confirm, ad-hoc receiving |
| `views/suppliers.py` | 530 | Supplier CRUD, bulk operations |
| `views/items/` | — | Items list, detail, stock operations (submodule) |
| `views/stock_take.py` | 199 | Physical count workflow |
| `views/settings.py` | 266 | Units, categories, departments reference data |
| `views/api.py` | 183 | DRF ViewSets |
| `views/explore.py` | — | Explore/search page |
| `views/ml.py` | — | Demand forecasting dashboard |
| `views/visualizations.py` | — | Charts (Plotly, Chart.js) |

---

## 7. Services Reference

| File | Purpose |
|------|---------|
| `item_service.py` | Item CRUD, stock status, ABC classification |
| `recipe_service.py` | Recursive cost calculation, sub-recipe handling |
| `stock_service.py` | Stock movements, adjustments, wastage |
| `indent_consolidation_service.py` | Group indent items into PO suggestions |
| `goods_receiving_service.py` | GRN confirmation, indent auto-fulfilment |
| `purchase_order_service.py` | PO workflows, status transitions |
| `purchase_order_kpis.py` | PO analytics and KPIs |
| `kpis.py` | Dashboard KPIs (low stock, pending orders, costs) |
| `dashboard_service.py` | Dashboard data aggregation |
| `list_utils.py` | Generic filtering, sorting, pagination helpers |
| `form_service.py` | Dynamic form generation |
| `ml.py` | Holt-Winters demand forecasting |
| `snapshot_service.py` | Daily stock snapshot generation |
| `supplier_service.py` | Supplier CRUD operations |
| `department_service.py` | Department management |
| `categories_service.py` | Category/subcategory operations |
| `units_service.py` | Unit of measure management |
| `ui_service.py` | UI choice lists and options |
| `exceptions.py` | Custom exception hierarchy |

---

## 8. URL Naming Convention

Pattern: `<module>-<action>`

```
indent-list          indent-detail        indent-create
indent-update        indent-approve       indent-cancel
po-list              po-detail            po-create-partial
grn-list             grn-create           grn-create-adhoc
stock-take-list      stock-take-create    stock-take-count
recipe-list          recipe-detail        recipe-create
item-list            item-detail          item-create
supplier-list        consolidation-preview
```

Partial views (for HTMX drawers) use a `-partial` suffix.

---

## 9. Template Conventions

### File naming
| Pattern | Example | Purpose |
|---------|---------|---------|
| `feature_list.html` | `indent_list.html` | Full list page |
| `feature_detail.html` | `recipe_detail.html` | Full detail page |
| `_feature_partial.html` | `_po_create_partial.html` | HTMX drawer content |
| `_feature_table.html` | `_indents_table.html` | Table fragment |
| `_feature_section.html` | `_stock_section.html` | Page section fragment |

### Reusable components (in `templates/components/`)
```
_base.html              Master layout (nav, sidebar, footer)
button.html             Styled button with variants
form_field.html         Labelled input with error display
modal.html              Dialog overlay
tabs.html               Tab switcher
list_layout.html        Standard list page scaffold
detail_layout.html      Standard detail page scaffold
kpi_card.html           Dashboard metric card
pagination.html         Page navigation
filter_bar.html         Filter/search bar
empty_state.html        No-results placeholder
toast.html              Flash notification
breadcrumb.html         Page breadcrumb trail
responsive_table.html   Mobile-friendly table
alert.html              Inline alert message
```

### Comments
Use HTML comments `<!-- -->` in templates, not Django `{# #}` comments — Django comments can appear as visible text when a partial is loaded outside its full template context.

---

## 10. Static JS Files

| File | Purpose |
|------|---------|
| `modal.js` | Drawer/modal open, close, HTMX loading |
| `items-table.js` | Items list filtering, sorting, row selection |
| `recipe-components.js` | Recipe ingredient form (add/remove rows) |
| `indent-form.js` | Indent form auto-add rows, validation |
| `predictive-dropdown.js` | Searchable single-select |
| `predictive-multiselect.js` | Searchable multi-select |
| `multiselect-chips.js` | Chip-style multi-select |
| `notifications.js` | Toast notifications |
| `smart-forms.js` | Auto-submit, inline validation |
| `column-filters.js` | Dynamic column filter dropdowns |
| `tables.js` | Sticky headers, column sorting |
| `forms.js` / `formset.js` | Generic form utilities, formset row management |
| `top-nav.js` | Navigation interactions |

JS tests live in `static/js/*.test.js` and run via `npm test`.

---

## 11. Middleware Stack (in order)

```
SecurityMiddleware                          Django built-in
WhiteNoiseMiddleware                        Static file serving
SessionMiddleware                           Django built-in
CommonMiddleware                            Django built-in
CsrfViewMiddleware                         Django built-in
AuthenticationMiddleware                    Django built-in
DetailedErrorLoggingMiddleware             core — logs full 500 tracebacks (prod only)
LoginRequiredMiddleware                    core — redirects unauthenticated to login
LazyStockSnapshotMiddleware                inventory — generates snapshots lazily
MessageMiddleware                           Django built-in
XFrameOptionsMiddleware                    Django built-in
```

Two additional middleware are defined but inactive:
- `core.performance_middleware.PerformanceMonitoringMiddleware` — tracks query counts and response time. Add to `MIDDLEWARE` in `base.py` to enable.

---

## 12. Management Commands

```bash
# Used in production build (render.yaml / build.sh)
python manage.py create_default_superuser
python manage.py reset_admin_password
python manage.py setup_cache

# Useful for dev/demo
python manage.py populate_business_data   # seed demo data
python manage.py snapshot_stock           # manual stock snapshot
python manage.py train_models             # train ML forecasting models
python manage.py ensure_superuser         # idempotent superuser creation

# Dev utilities (rarely needed)
python manage.py debug_login
python manage.py performance_test
python manage.py render_items_page
```

---

## 13. Development Workflow

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp env/dev.example .env   # fill in DATABASE_URL etc.
python manage.py migrate
python manage.py populate_business_data

# Daily commands
make fmt      # format with Black
make lint     # lint with Ruff (auto-fix)
make test     # run pytest
make ci       # fmt + lint + test (run before every commit)

# Run locally
python manage.py runserver
```

### Branch & PR convention
```
Branch:   feature/<short-slug>
Base:     feature/django-refactor
PR title: fix: <what>, feat: <what>, chore: <what>, docs: <what>
```

---

## 14. Adding a New Feature — Checklist

1. **Model** — add fields, write migration (`python manage.py makemigrations`)
2. **Service** — business logic in `inventory/services/your_service.py`
3. **Form** — Django form or formset in `inventory/forms/your_forms.py`
4. **View** — thin view in `inventory/views/your_module.py`, use service
5. **URL** — add to `inventory/ui_urls.py` with `<module>-<action>` name
6. **Templates** — full page + partials, use components from `templates/components/`
7. **Nav** — add link to `templates/_base.html` sidebar if needed
8. **Tests** — add to `tests/test_your_module.py`
9. **Run** `make ci` before committing

---

## 15. Common Gotchas

| Problem | Cause | Fix |
|---------|-------|-----|
| Form submits to raw unstyled page | Native `form.submit()` in drawer | Use `fetch()` or `hx-post` |
| `NOT NULL constraint` on `line_total` | Forgot to compute PO line total | Set `line_total = qty × price` before save |
| Circular recipe cost loop | Sub-recipe references itself | `clean()` calls `_check_circular()` — always validate |
| Wrong numbers in cost calculations | Using `float` instead of `Decimal` | Import and use `decimal.Decimal` everywhere |
| Drawer buttons show for wrong status | Static buttons not status-conditional | Gate buttons on `object.status` in template |
| Django comment visible in partial | `{# comment #}` in included partial | Use `<!-- HTML comment -->` instead |
| 500 on any RecipeItem query | Missing `sub_recipe_id` column | Migration 0032 adds it — deploy to fix |
| Render cold start delay | Free tier sleeps after 15min | First request takes ~50s — expected |

---

## 16. What Can Be Safely Ignored / Is Legacy

| Item | Status |
|------|--------|
| `docs/archive/` | Historical analysis docs — reference only, not maintained |
| `core/performance_middleware.py` | Defined, not active — enable in `base.py` if needed |
| `inventory/services/supabase_cache.py` | Supabase removed from deps — dead code |
| `inventory/services/sale_service.py` | SaleTransaction model exists but rarely used |
| `static/js/*.test.js` | JS unit tests — run via `npm test`, not pytest |
| `db/` app directory | Empty app placeholder — no models or views |
| `nginx/` directory | Nginx config — not used on Render (uses gunicorn directly) |
