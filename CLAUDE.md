# Inventory Pro — CLAUDE.md

## Project Overview

Inventory Pro is a Django-based F&B (Food & Beverage) inventory management app for restaurant and cafe operations. It covers the full procurement-to-stock pipeline: Indents → Purchase Orders → GRN (Goods Received Notes) → Stock Movements, plus Recipe costing, Food Cost reporting, and ML-based demand planning.

**Live URL:** https://inventory-app-kguo.onrender.com/
**Hosting:** Render.com free tier — a background keep-alive thread pings the app every 5 min to prevent idle sleep (see `inventory/apps.py`). Set `DISABLE_KEEP_ALIVE=true` to suppress.

## Tech Stack

- **Backend:** Django 5.2 (Python)
- **Frontend:** Django templates + HTMX for AJAX interactions + Alpine.js for some reactivity
- **CSS:** Tailwind CSS (utility classes: `px-4 py-2 rounded-lg bg-surface text-bodyText`, etc.)
- **Charts:** Plotly (Receipts Over Time, Stock Activity Heatmap), Chart.js (some dashboard widgets)
- **Database:** PostgreSQL (hosted on Render)
- **No separate frontend build step** — all JS/CSS is served via Django static files

## Architecture Patterns

### HTMX + Drawer Pattern

Most create/edit forms use a drawer (slide-in panel) loaded via HTMX:

- Trigger buttons have `data-modal-url="/some/partial/"` and `data-modal-type="drawer"`
- A delegated JS click handler intercepts these and fetches the partial HTML into a drawer container
- Form submissions inside drawers should use `fetch()` or `hx-post` to POST via AJAX and return JSON
- **Common bug pattern:** If a form inside a drawer uses native `<form>` submission instead of AJAX, it navigates to the partial URL as a raw unstyled page. Always ensure drawer forms submit via fetch/HTMX.

### JSON Response Convention

Create/update views that serve drawers should return JSON for AJAX requests:

```python
if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
    return JsonResponse({'ok': True, 'id': obj.pk})
```

### Django Formsets

PO line items and recipe ingredients use Django formsets with management fields (`items-TOTAL_FORMS`, `items-0-item`, etc.). Always include the management form in templates.

### Navigation

Navigation is driven from `inventory_app/navigation.py` — groups and links are defined there, not hardcoded in templates. To add a nav item, add an entry to `NAVIGATION_GROUPS` and register the icon in `templates/components/top_nav.html`.

## Key Models & Relationships

```
Indent → IndentItem (items with quantity, unit)
  ↓ (via Consolidation Planner)
PurchaseOrder → PurchaseOrderItem (line_total = quantity_ordered × unit_price)
  ↓
GRN (GoodsReceivedNote) → GRNItem
  ↓ (auto-creates on confirm)
StockTransaction (types: RECEIVING, ADJUSTMENT, WASTAGE, TRANSFER, SALE, ISSUE)
  - reason_category: STOCK_TAKE, MANUAL, etc.

Recipe → RecipeItem → Item (raw ingredient) OR Recipe (sub-recipe)
  - selling_price, food_cost_percentage (computed property)
  - Recursive costing for sub-recipes

StockTake → StockTakeItem (system_qty vs physical_qty)
  - On completion: auto-generates ADJUSTMENT StockTransactions for variances
  - Updates Item.current_stock atomically via F() expressions

Department — used for indent assignment and stock transfers
Supplier — linked to POs and GRNs
Item — has current_stock, reorder_point, moq, unit, category, department, ABC class
```

## Status Flows

### Indent Statuses

`SUBMITTED → APPROVED → PROCESSING → COMPLETED`
(Also: `CANCELLED` from any active state)

- Only SUBMITTED and APPROVED can be edited
- Drawer buttons are status-conditional

### PO Statuses

`DRAFT → SENT (to Supplier) → RECEIVED`

- Migration `simplify_po_statuses` consolidated old 5-status flow

### GRN

`DRAFT → RECEIVED`

- On confirmation, auto-fulfills connected indents
- Supports ad-hoc GRNs without a PO

### Stock Take

`DRAFT → IN_PROGRESS → COMPLETED`

- On completion, generates ADJUSTMENT transactions for all counted items with variance
- Uncounted items are left unchanged

## Important Conventions

### PurchaseOrderItem.line_total

The `line_total` column has a NOT NULL constraint. It must always be computed as `quantity_ordered × unit_price` before saving. The model's `save()` method has a safety net, but views should also compute it explicitly.

### Template Comments

Use HTML comments (`<!-- -->`) not Django template comments (`{# #}`) for any comment that might appear in an included partial — Django comments can leak as visible text if the partial is loaded outside a template context.

### StockTransaction Types

- **RECEIVING** — goods arriving from supplier (via GRN or direct receive)
- **ADJUSTMENT** — correcting stock levels (manual correction or stock-take variance)
- **WASTAGE** — food thrown away (spoiled, expired, dropped, over-prepped)
- **TRANSFER** — between departments (Kitchen ↔ Bar ↔ Pastry etc.)
- **SALE** — auto-deducted when a recipe sale is recorded
- **ISSUE** — stock issued to a department

### Recipe Sub-recipes

RecipeItem can reference either an `item` (raw ingredient) OR a `sub_recipe` (another Recipe). Validation prevents circular dependencies. Cost calculation is recursive with a visited-set guard.

### Decimal Arithmetic in Templates

Django templates cannot do arithmetic with Decimal values. If you need a computed value in a template (e.g. `remaining = ordered - received`), add a `@property` on the model and reference it as `{{ obj.remaining }}`.

## URL Naming Conventions

URLs use underscores: `<module>_<action>` e.g.:

- `indent_list`, `indent_detail`, `indent_create`, `indent_update`
- `po_list`, `po_create_partial`, `grn_create`, `grn_create_adhoc`
- `stock_take_list`, `stock_take_start`, `stock_take_count`, `stock_take_review`
- `food_cost_report`, `history_reports`, `recipes_list`

Partial views (for drawers) typically have `_partial` suffix in the URL name.

## Development Workflow

### Standard Process (per task)

1. Create a feature branch from `feature/django-refactor`:
   `git checkout -b feature/<slug> origin/feature/django-refactor`
2. Make changes
3. Run `make ci` (formats with Black, lints with Ruff, runs pytest)
4. Commit and push: `git push -u origin feature/<slug>`
5. Claude opens a PR targeting `feature/django-refactor` with a clear description
6. User tests in the live preview
7. User confirms → Claude merges the PR

### Tooling (via Makefile)

| Command          | Purpose                                     |
| ---------------- | ------------------------------------------- |
| `make fmt`       | Format with Black                           |
| `make lint`      | Lint with Ruff (auto-fix)                   |
| `make test`      | Run pytest                                  |
| `make ci`        | fmt + lint + test (run before every commit) |
| `make precommit` | Run all pre-commit hooks                    |
| `make coverage`  | Tests with coverage report                  |

### Python Environment Detection

At the start of each session, detect the active Python env in order:

1. `.venv/bin/python` (local venv)
2. `venv/bin/python`
3. `which python` (system or active virtualenv)

All `make` commands invoke the environment-appropriate Python automatically.

### Environment Variables / Secrets

- Ask the user for any required secret (DATABASE_URL, SECRET_KEY, etc.) on first need
- Store in a `.env` file at the project root (gitignored)
- Tests use `env/test.example` — no real secrets needed for `make test`

### PR Naming Convention

- Branch: `feature/<short-task-slug>`
- PR title: `<verb>: <what changed>` e.g. `fix: indent drawer submit`, `feat: food cost report`
- Target branch: `feature/django-refactor`

### Task Planning

Tasks are discussed and planned collaboratively at the start of each session. The user directs priorities.

## Common Gotchas

1. **Render keep-alive:** A background thread in `inventory/apps.py` pings the app every 5 min. If you see the app still sleeping, check `DISABLE_KEEP_ALIVE` isn't set and verify the thread is running in Render logs (`[keep-alive] 200`).
2. **form.submit() in drawers:** Never use native `form.submit()` — it causes full-page navigation to the partial endpoint. Always use `fetch()` or HTMX.
3. **line_total on PO items:** Forgetting to compute this before save causes `NOT NULL constraint violation`. Always set `line_total = quantity_ordered * unit_price`.
4. **Status-conditional buttons:** Indent and PO drawer/detail pages must show different action buttons based on current status. Never show all buttons statically.
5. **Decimal precision:** Use `Decimal` (not `float`) for all monetary and quantity calculations. Import from `decimal`.
6. **Circular sub-recipes:** The `_check_circular()` method on RecipeItem prevents A→B→A loops. Always call `clean()` before saving recipe items.
7. **Template arithmetic:** Don't attempt Decimal math in Django templates. Add a `@property` on the model instead.

## Completed Work Log

Track what's been built so future sessions have context. Newest first.

### Phase D — Domain Gaps (March 2025)

- **Stock-take auto-adjust**: Completing a stock take generates ADJUSTMENT StockTransactions for all items with variance and updates `Item.current_stock` atomically. `reason_category="STOCK_TAKE"` tags these transactions.
- **Food cost report**: `/recipes/food-cost-report/` — lists all active FINAL recipes with ingredient cost, selling price, food cost %, target %, gross margin, and status badges. Filterable by status. Added to "Insights & Settings" nav.
- **Keep-alive thread**: Background daemon thread in `InventoryConfig.ready()` pings the app URL every 5 min to prevent Render idle sleep.

### Phase C — UX Confusion (March 2025)

- Replaced hardcoded user list in indent filter with live DB query
- Added "Remaining" column on PO receive form (model `@property` pattern for template arithmetic)
- Added uncounted-items warning + confirmation guard on stock-take review page
- Confirmed nav was already clean (no table/card sub-URLs, workflow guide already present)

### Phase B — Known Bugs (March 2025)

- Status-conditional buttons on indent and PO drawers
- Various P1/P2 bug fixes from audit

### Phase A — Core Workflow (March 2025)

- Fixed PO creation (removed invalid `po_number` kwarg)
- Fixed `line_total` NOT NULL constraint (model `save()` safety net + view computation)
- Fixed consolidation planner → PO creation pipeline
