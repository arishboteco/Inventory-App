# Inventory Pro UI Contract, Conformance Checklist, and Rollout Plan

> Status: **Contract-first document**. This defines the canonical UI rules and migration checklist before page-level refactors begin.

## Goal (single comprehensive task)

Unify list pages and forms under one predictable UI system by standardizing shared components, semantic design tokens, and behavior contracts. This reduces duplicate template markup, improves dark-mode consistency, and keeps HTMX interactions uniform.

---

## 1) Canonical UI contract

### 1.1 Page header area contract

Base component: `templates/components/create_manage_layout.html`

#### Canonical structure (top to bottom)
1. `page_eyebrow` (optional context tag)
2. `page_heading` (**required**)
3. `page_subtitle` (optional one-line context)
4. `page_meta` (optional KPI/meta chips)
5. Right action rail:
   - `secondary_actions` row (filters reset, export, view switch, more menu)
   - `primary_actions` row (create/new/import)
6. `hero_extra` (optional for page-specific auxiliary controls)

#### Header rules
- Primary action appears in the **bottom-right action row** (`primary_actions`).
- Secondary actions appear above primary actions in `secondary_actions`.
- KPI/meta chips live in `page_meta`, not custom ad-hoc containers.
- Do not place filters inside header action buttons; filters belong in the filter row.

#### Canonical chip styles
- Informational chip: `bg-info-soft text-info-text border border-border`
- Success chip: `bg-success-soft text-success-text border border-border`
- Warning chip: `bg-warning-soft text-warning-text border border-border`
- Danger chip: `bg-danger-soft text-danger-text border border-border`

---

### 1.2 Filter row behavior and layout contract

Base component: `templates/components/filter_bar.html`

#### Canonical layout
- A single filter form (`id="filters"`) directly under header.
- Responsive order:
  1. Search
  2. Select filters (status/category/etc.)
  3. Date range filters (from/to)
  4. View toggle
  5. Export
  6. Page size
  7. Bulk-action trigger (if selection mode active)

#### HTMX behavior rules
- Search: `hx-trigger="keyup changed delay:300ms"` (default delay).
- Select/date/page-size controls: `hx-trigger="change"`.
- All controls include the full filter context via `hx-include="#filters"`.
- All list updates target a single table target (`hx-target` passed from page).
- Preserve state with hidden fields for sort/direction/layout/page_size as needed.

#### Filter reset behavior
- Provide one clear/reset control in `secondary_actions` or at filter row end.
- Reset removes query/filter params but preserves safe layout defaults when intended.

---

### 1.3 Table container, empty state, loading skeleton, pagination contract

Base slot structure from `create_manage_layout.html`:
- `table_container`
  - `table_id`
  - `data_container`
  - `bulk_actions`
  - `pagination`

#### Canonical table shell
- Use one bordered surface card wrapper for each table region:
  - `bg-surface border border-border rounded-2xl shadow-card`
- Table headers use semantic table tokens:
  - `bg-tableHeader text-tableHeaderText border-tableBorder`

#### Empty state contract
- Empty state appears in `data_container` when result set is zero.
- Must include:
  - Clear title
  - One sentence explaining what happened
  - Primary recovery action (clear filters or create first record)

#### Loading contract
- HTMX loading indicator is always provided through `hx-indicator`.
- Skeleton uses surface/border tokens only (avoid raw gray utilities).

#### Pagination contract
- Pagination appears in `pagination` block below table content.
- Page size control is part of filter contract, not ad-hoc inside random table footers.

---

### 1.4 Drawer/modal form structure and button order

Base component: `templates/components/form_layout.html`

#### Canonical form structure
1. Form header card (`heading`, optional `heading_badge`, `form_summary`)
2. Form body card (`form_body` with fields)
3. Errors:
   - non-field errors at top of form body
   - field errors directly below each field

#### Canonical action order
- In LTR context, right-aligned action group order:
  1. **Primary submit** (Save/Create/Update)
  2. **Secondary cancel/back**
- Destructive confirmations use dedicated danger variant and explicit confirmation copy.

#### Modal/drawer behavior
- Same field and action structure as full-page form.
- Focus should land on first interactive element.
- ESC and close actions should map to cancel semantics where safe.

---

## 2) Shared component normalization contract (before page migration)

### Required expansions

#### `filter_bar` must support explicit props/slots for:
- Search input
- Select filters (single/multi)
- Date range pair
- View toggle control
- Export action trigger
- Page size selector
- Bulk action trigger area

#### `create_manage_layout` must remain canonical for:
- Header slots
- Filter slot
- Table/pagination/bulk-action slots

#### `button` component variants
- Ensure standard variants cover list/form needs:
  - `primary`, `secondary`, `ghost`, `danger`, `accent`, `square`
- Avoid page-local custom button class stacks unless truly unique.

### HTMX compatibility requirements
- Components must allow passthrough attributes for `hx-get`, `hx-target`, `hx-trigger`, `hx-include`, `hx-indicator`, `hx-push-url` where needed.
- Avoid hard-coding endpoints inside shared components when endpoint is page-specific.

---

## 3) Design token standardization contract

Base token source: `static/src/app.css`

### Token usage rule
- Prefer semantic classes backed by token variables (`bg-surface`, `text-bodyText`, `border-border`, etc.).
- Reduce template-level raw gray utility usage (`text-gray-*`, `bg-gray-*`, `border-gray-*`).

### Dark mode rule
- Dark-mode behavior must be driven by token variables in CSS, not one-off per-template overrides.
- Existing dark utility fallback mappings are transitional only and should shrink over time.

### Migration pass target scopes
- `templates/inventory/`
- `templates/components/`

### Raw-to-token mapping guide (default)
- `text-gray-700` → `text-bodyText`
- `text-gray-500` → `text-tableHeaderText` or semantic status text token (context-dependent)
- `bg-gray-50` → `bg-tableHeader`
- `bg-gray-100` → `bg-surfaceSubtle`
- `border-gray-200` / `border-gray-300` → `border-border`

---

## 4) Outlier migration priority

### Highest-impact first
1. `templates/inventory/purchase_orders/list.html` (**first migration target**)
2. Then align other high-traffic list pages to the same pattern.

### Mandatory constraints during migration
- Preserve business behavior and HTMX endpoints.
- Replace custom layout/control markup with `create_manage_layout` + `filter_bar` conventions.
- Keep action hierarchy and filter behavior per this contract.

---

## 5) Form rendering strategy contract

### Single strategy decision
- Use componentized field rendering with `templates/components/form_field.html`.
- Keep widget styling centralized via `inventory/forms/base.py` (`StyledFormMixin`).

### First reference templates to normalize
- `templates/inventory/indent_form.html`
- `templates/inventory/_item_form_partial.html`
- `templates/inventory/_supplier_form_partial.html`

### Form consistency rules
- Labels: consistent text size/weight and spacing above control.
- Help text: below control, before errors (or one fixed project-wide order).
- Errors: directly associated with field, consistent color/token usage.
- Actions: submit first, cancel second; visual hierarchy must match intent.

---

## 6) Interaction consistency rules

### Actions & menus
- Primary action: `primary_actions` area in header.
- “More” menu: secondary area, right-aligned with other secondary controls.
- Bulk actions: only visible when rows are selected; anchored in `bulk_actions` block.

### Filter trigger rules
- Search delay: 300ms default.
- Select/date/page-size: change trigger.
- Reset: one explicit control clears filters and refreshes list.

### Feedback states
- Loading: use a consistent indicator/skeleton pattern.
- Empty: one standard empty-state layout.
- Confirmations: danger semantics and consistent button order/copy.

---

## 7) UI conformance gate (lightweight)

## PR checklist (copy into PR template or description)
- [ ] Uses shared layout/component (`create_manage_layout`, `filter_bar`, `form_layout`, `button`, `form_field` where relevant)
- [ ] Uses semantic tokens instead of raw gray utility classes
- [ ] Matches filter/form interaction standards (HTMX trigger/reset/search delay)
- [ ] Preserves accessibility (labels, focus ring visibility, keyboard interaction)
- [ ] Preserves business behavior and endpoints

## Simple static checks (pre-commit/CI helper commands)

```bash
# 1) Detect raw gray utility drift in inventory + components templates
rg -n "text-gray-|bg-gray-|border-gray-" templates/inventory templates/components

# 2) Detect hand-coded filter forms not using shared filter_bar include/component patterns
rg -n "id=\"filters\"|hx-include=\"#filters\"" templates/inventory

# 3) Detect direct button class stacks where shared button component should be used
rg -n "inline-flex items-center px-4 py-2" templates/inventory templates/components
```

## Contributor-facing guideline location
- Keep this file near templates so contributors can apply standards while editing.

---

## 8) Rollout plan and measurement

## Wave rollout

### Wave 1 (high traffic)
- Items
- Purchase Orders
- Suppliers
- Indents
- Stock Movements
- Recipes

### Wave 2
- Remaining inventory pages and partials

## Measurable success criteria
- Fewer unique filter/form patterns in templates.
- Less duplicated button/filter markup at template level.
- Fewer dark-mode-specific override rules required in CSS.

## Suggested baseline tracking
Run before Wave 1 and after each wave:

```bash
# Count raw gray utility usage
rg -n "text-gray-|bg-gray-|border-gray-" templates/inventory templates/components | wc -l

# Count duplicated button stacks
rg -n "inline-flex items-center px-4 py-2" templates/inventory templates/components | wc -l

# Count direct custom filter forms
rg -n "<form[^>]*id=\"filters\"" templates/inventory | wc -l
```

Use deltas to confirm convergence toward the shared contract.
