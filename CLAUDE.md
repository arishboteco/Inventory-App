# Inventory Pro — CLAUDE.md

## Project Overview

Inventory Pro is a Django-based F&B (Food & Beverage) inventory management app for restaurant and café operations. It covers the full procurement-to-stock pipeline: Indents → Purchase Orders → GRN (Goods Received Notes) → Stock Movements, plus Recipe costing, Reporting, and ML-based demand planning.

**Live URL:** https://inventory-app-kguo.onrender.com/
**Login:** admin / admin123!
**Hosting:** Render.com free tier (cold starts ~50-60s)

## Tech Stack

- **Backend:** Django (Python)
- **Frontend:** Django templates + HTMX for AJAX interactions + Alpine.js for some reactivity
- **CSS:** Bootstrap 5
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

## Key Models & Relationships

```
Indent → IndentItem (items with quantity, unit)
  ↓ (via Consolidation Planner)
PurchaseOrder → PurchaseOrderItem (line_total = quantity_ordered × unit_price)
  ↓
GRN (GoodsReceivedNote) → GRNItem
  ↓ (auto-creates on confirm)
StockMovement (types: RECEIVING, ADJUSTMENT, WASTAGE, TRANSFER)

Recipe → RecipeItem → Item (raw ingredient) OR Recipe (sub-recipe)
  - selling_price, food_cost_percentage (computed property)
  - Recursive costing for sub-recipes

Department — used for indent assignment and stock transfers
Supplier — linked to POs and GRNs
Item — has current_stock, reorder_point, moq, unit, category, department, ABC class
```

## Status Flows

### Indent Statuses
`SUBMITTED → APPROVED → PROCESSING → COMPLETED`
(Also: `CANCELLED` from any active state)
- Only SUBMITTED and APPROVED can be edited
- Drawer buttons must be status-conditional (Phase B fix)

### PO Statuses (simplified in Phase C)
`DRAFT → SENT (to Supplier) → RECEIVED`
- Previously was 5 statuses (Draft → Submitted → Approved → Processing → Completed)
- Migration `simplify_po_statuses` consolidated old values

### GRN
`DRAFT → RECEIVED`
- On confirmation, auto-fulfills connected indents (Phase C fix)
- Supports ad-hoc GRNs without a PO (Phase D)

## Important Conventions

### PurchaseOrderItem.line_total
The `line_total` column has a NOT NULL constraint. It must always be computed as `quantity_ordered × unit_price` before saving. The model's `save()` method has a safety net, but views should also compute it explicitly.

### Template Comments
Use HTML comments (`<!-- -->`) not Django template comments (`{# #}`) for any comment that might appear in an included partial — Django comments can leak as visible text if the partial is loaded outside a template context.

### Stock Movement Types
- **RECEIVING** — goods arriving from supplier (via GRN or direct receive)
- **ADJUSTMENT** — correcting a counting error only
- **WASTAGE** — food thrown away (spoiled, expired, dropped, over-prepped)
- **TRANSFER** — between departments (Kitchen ↔ Bar ↔ Pastry etc.)

### Recipe Sub-recipes
RecipeItem can reference either an `item` (raw ingredient) OR a `sub_recipe` (another Recipe). Validation prevents circular dependencies. Cost calculation is recursive with a visited-set guard.

## URL Naming Conventions

URLs follow the pattern: `<module>-<action>` e.g.:
- `indent-list`, `indent-detail`, `indent-create`, `indent-update`
- `po-list`, `po-create-partial`, `grn-create`, `grn-create-adhoc`
- `stock-take-list`, `stock-take-create`, `stock-take-count`, `stock-take-review`
- `consolidation-preview`, `low-stock-indent`

Partial views (for drawers) typically have `-partial` suffix in the URL name.

## Production Readiness Status

### Completed
- **Phase A:** Core pipeline unblocked (PO creation, line_total fix, Quick PO)
- **Phase B:** Known bugs fixed (Indent edit/submit/drawer buttons, MOQ message, department dedup)
- **Phase C:** UX confusion removed (guidance text, auto-fulfill, naming, source column, PO status simplification, help panels)
- **Phase D:** Critical missing features (sub-recipes, Food Cost %, stock transfers, stock-take, low-stock indent, ad-hoc GRN)

### Remaining
- **Phase E:** Data Quality & Reporting — Food cost reports, merge duplicate pages, allergens, prep instructions, wastage reason codes
- **Phase F:** Scale & Compliance — Batch/lot tracking, consumption tracking, multi-outlet, role-based access, mobile views, scheduled reports

See `/outputs/inventory-pro-production-roadmap.md` for the full phased plan.

## Common Gotchas

1. **Render cold starts:** The free tier sleeps after 15 min inactivity. First request takes 50-60s. Use sequential waits if automating.
2. **form.submit() in drawers:** Never use native `form.submit()` — it causes full-page navigation to the partial endpoint. Always use `fetch()` or HTMX.
3. **line_total on PO items:** Forgetting to compute this before save causes `NOT NULL constraint violation`. Always set `line_total = quantity_ordered * unit_price`.
4. **Status-conditional buttons:** Indent and PO drawer/detail pages must show different action buttons based on current status. Never show all buttons statically.
5. **Decimal precision:** Use `Decimal` (not `float`) for all monetary and quantity calculations. Import from `decimal`.
6. **Circular sub-recipes:** The `_check_circular()` method on RecipeItem prevents A→B→A loops. Always call `clean()` before saving recipe items.
