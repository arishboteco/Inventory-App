# Page Architecture, Coding, and Design Audit

## Scope and how this audit was done

This review focuses on the main user-facing pages (dashboard, list pages, detail pages, form pages, and reporting pages) wired in `inventory/ui_urls.py` plus core dashboard/auth pages. The goal is to explain:

1. **Architecture** (how each page is built: view + template + services).
2. **Coding pattern** (Class-based vs function-based views, filtering, partials, form handling).
3. **Design pattern** (layout template, shared components, interaction model).
4. **Standardization opportunities** (where similar pages behave differently today).

---

## 1) System-level page architecture (current state)

### A. URL → View composition

The app has a clear split between API routes (`inventory/urls.py`) and UI routes (`inventory/ui_urls.py`). UI pages are mostly server-rendered Django templates with selective HTMX partial refreshes. This gives quick initial render and progressively enhanced interactivity.

### B. Layering pattern used across most pages

A common layered pattern appears repeatedly:

- **View layer**: gathers request params, orchestrates filtering/pagination/form actions.
- **Service layer**: business logic (stock updates, KPI calcs, purchase workflows, recipes, etc.).
- **Template layer**: standard layouts + reusable components + partial templates.

This is strong overall architecture, but adoption is not completely uniform between older and newer pages.

### C. Layout system

There is an explicit reusable layout family:

- `components/create_manage_layout.html` for list/overview pages.
- `components/detail_layout.html` for entity detail pages.
- `components/form_layout.html` for form-heavy pages.

These provide standard slots for heading, actions, filters, table/data area, and page scripts. This is a good foundation for visual consistency.

---

## 2) Page-by-page differences and features

> Legend:
>
> - **Layout** = base template style.
> - **Interaction model** = full page / HTMX partial / modal-drawer hybrids.
> - **Notes** = standout differences vs the rest of the app.

### Insights pages

| Page                               | Primary route      | Layout                                    | Interaction model                 | Key differences / features                                                                       |
| ---------------------------------- | ------------------ | ----------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------ |
| Dashboard (Overview)               | `root`             | `core/dashboard.html`                     | Full page + partial KPI endpoint  | Rich KPI bundle + alert panel + trend JSON data; separate core app namespace vs inventory pages. |
| Food Cost                          | `food_cost_report` | `inventory/recipes/food_cost_report.html` | Mostly full page                  | Lives under recipe domain but conceptually an insights page.                                     |
| History                            | `history_reports`  | `components/create_manage_layout.html`    | HTMX-aware filtering              | Uses history tabs/partials and report-style workflow.                                            |
| Stock Charts                       | `visualizations`   | `components/create_manage_layout.html`    | Full page with chart data in JSON | Function-based view computes daily series and renders chart payloads.                            |
| Reorder Suggestions (ML Dashboard) | `ml_dashboard`     | `components/create_manage_layout.html`    | Full page + POST recompute        | Synchronous recompute + cache usage; blends analytics and operations.                            |

### Procurement pages

| Page                        | Primary route                                      | Layout                                     | Interaction model                      | Key differences / features                                                 |
| --------------------------- | -------------------------------------------------- | ------------------------------------------ | -------------------------------------- | -------------------------------------------------------------------------- |
| Indents list                | `indents_list`                                     | `components/create_manage_layout.html`     | HTMX table refresh                     | Strong list/table split with filters and status workflows.                 |
| Indent detail               | `indent_detail`                                    | `components/detail_layout.html`            | Full page + optional partial rendering | Supports partial detail rendering for drawer/edit scenarios.               |
| Indent create/update        | `indent_create` / `indent_update`                  | `components/form_layout.html`              | Full form + drawer partials            | Hybrid form strategy (full page and modal partial).                        |
| Order Planner (Consolidate) | `indents_consolidate_preview`                      | `components/create_manage_layout.html`     | Full page action flow                  | A planner-style flow that behaves like a wizard step.                      |
| Purchase Orders list        | `purchase_orders_list`                             | `components/create_manage_layout.html`     | HTMX table/cards + view mode switch    | Most advanced list page (KPIs, table/cards toggle, progress bars, export). |
| PO detail / receive         | `purchase_order_detail` / `purchase_order_receive` | `detail_layout` + `form_layout`            | Full page + partial modal endpoints    | Has a mature partial endpoint set for create/edit/receive drawers.         |
| GRN list                    | `grn_list`                                         | `components/create_manage_layout.html`     | List page with quick form options      | Consistent with list architecture.                                         |
| GRN create/detail           | `grn_create` / `grn_detail`                        | `_base` (create), `detail_layout` (detail) | Full page forms/details                | Create page uses raw `_base` rather than shared `form_layout`.             |

### Stock pages

| Page                           | Primary route                                               | Layout                                 | Interaction model                                  | Key differences / features                                                              |
| ------------------------------ | ----------------------------------------------------------- | -------------------------------------- | -------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Stock Movements                | `stock_movements`                                           | `components/create_manage_layout.html` | Multi-form page with modal sections + flash-reopen | Large function-based workflow handling receiving/adjust/waste/transfer in one endpoint. |
| Stock Count list               | `stock_take_list`                                           | `components/create_manage_layout.html` | Full page list                                     | High-level entry screen for stock take sessions.                                        |
| Stock Count start/count/review | `stock_take_start`, `stock_take_count`, `stock_take_review` | `_base` templates                      | Full-page task flow                                | Operationally a wizard, but visually/layout-wise separate from form/detail layouts.     |

### Master data pages

| Page                      | Primary route                                 | Layout                                   | Interaction model                               | Key differences / features                                                    |
| ------------------------- | --------------------------------------------- | ---------------------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------------- |
| Items list                | `items_list`                                  | `components/create_manage_layout.html`   | HTMX table + filters + inline create options    | Very feature-rich filters (category/subcategory/dept/stock-state) and export. |
| Item detail/edit/delete   | `item_detail` etc.                            | `detail_layout` + `form_layout` partials | Full page + inline/partial updates              | Good separation of detail and partial edit fragments.                         |
| Recipes list              | `recipes_list`                                | `components/create_manage_layout.html`   | Table/cards patterns + partial create/edit/view | Strong partial ecosystem; supports recipe-specific line-item behaviors.       |
| Recipe detail             | `recipe_detail`                               | `components/form_layout.html`            | Full page + partial fragments                   | Detail rendered in a form-style layout, unlike most detail pages.             |
| Suppliers list            | `suppliers_list`                              | `components/create_manage_layout.html`   | HTMX table/cards + inline create/bulk upload    | Similar to PO list in flexibility; includes bulk delete/upload flows.         |
| Supplier cards standalone | `suppliers_cards`                             | `_base`                                  | HTMX fragment use case                          | Duplicate presentation path that does not inherit list layout.                |
| Settings/Profile/Password | `settings`, `profile-edit`, `change-password` | `create_manage_layout` / `form_layout`   | Mostly full form pages                          | Settings page is list-style layout, profile/password are form-style.          |

### Utility and supporting pages

| Page                        | Route                                     | Layout               | Notes                                                   |
| --------------------------- | ----------------------------------------- | -------------------- | ------------------------------------------------------- |
| Workflow guide              | `workflow_guide`                          | `_base`              | Informational documentation page, intentionally custom. |
| Login / password reset info | `/accounts/login/`, `password_reset_info` | standalone templates | Auth pages are stylistically separate from app shell.   |

---

## 3) What is already standardized well

1. **Reusable layout primitives exist and are good quality.** The `create_manage`, `detail`, and `form` layouts provide a clean slot-based pattern.
2. **Partial rendering strategy is established.** Many domains provide `list + table partial + form partial` combinations.
3. **Service-oriented business logic is common.** Core workflows (stock, purchasing, KPIs) often call dedicated services rather than embedding heavy logic in templates.
4. **Navigation is centrally defined.** The grouped nav config is clear and maintainable.

---

## 4) Biggest inconsistencies and standardization opportunities

## Opportunity 1 — Standardize page shells to the 3 canonical layouts

**Issue:** Several pages still extend `_base` directly (`grn_create`, stock-take step pages, supplier cards standalone), while most pages use component layouts.

**Why it matters (plain English):** users feel small UI jumps between pages; developers re-solve the same spacing/header/action problems repeatedly.

**Recommendation:**

- Make `form_layout` default for create/update steps.
- Make `detail_layout` default for detail screens.
- Keep `_base` only for exceptional pages (auth, static guide-like docs, error pages).

## Opportunity 2 — Adopt one list-page contract everywhere

**Issue:** List pages are close but not identical in query params, context naming, and toggle behavior.

**Recommendation (single contract):**

- Shared query params: `q`, `status`, `active`, `sort`, `direction`, `page`, `page_size`, `view`.
- Shared context keys: `page_obj`, `page_size`, `querystring`, `export_url`, `container_id`, `view`.
- Shared endpoints: `/table/` partial required, `/cards/` optional when useful.

## Opportunity 3 — Reduce large multi-action views with “action handlers”

**Issue:** `stock_movements` and some procurement flows handle many actions in a single function body.

**Why it matters:** harder debugging, testing, onboarding.

**Recommendation:** split by action handler (receive/adjust/waste/transfer) with a thin orchestrator view.

## Opportunity 4 — Unify form submission behavior (HTMX vs JSON modal)

**Issue:** App currently uses a hybrid of HTMX partial flows and `data-modal-form` JSON handling.

**Recommendation:** choose one default (prefer HTMX pattern) and create an explicit compatibility layer for legacy modal endpoints.

## Opportunity 5 — Normalize “detail page” semantics

**Issue:** Recipe detail behaves more like a form layout than a detail layout.

**Recommendation:** define clear rule:

- Read-mostly entity pages use `detail_layout`.
- Edit-heavy pages use `form_layout`.

If recipe detail is primarily read-only with actions, migrate to `detail_layout` for consistency.

## Opportunity 6 — Introduce a page blueprint checklist

Create one short checklist used before merging any new page:

- Uses one of the canonical layouts.
- Has breadcrumbs + page title + primary action pattern.
- Uses standard list/filter/pagination params if it is a list page.
- Exposes predictable partial endpoint naming (`*_table`, `*_cards`, `*_form_partial`).
- Uses shared form error payload structure.

---

## 5) Suggested phased standardization plan (single comprehensive initiative)

### Phase 1 (Low risk, high consistency)

- Convert `_base` outlier operational pages to canonical layouts.
- Introduce a `Page Contract` doc in `docs/` and apply to one pilot module (e.g., suppliers).

### Phase 2 (Behavioral consistency)

- Standardize list query params/context names across items, suppliers, purchase orders, indents, recipes.
- Align table/cards partial endpoint naming and URL patterns.

### Phase 3 (Code architecture cleanup)

- Refactor large FBVs into action-specific handlers + shared service calls.
- Consolidate form submit/validation approach around HTMX-first flows.

### Phase 4 (Design consistency and QA guardrails)

- Add template lint checks for required blocks in canonical layouts.
- Add smoke tests that validate list contract behavior (filters/sort/pagination/view mode).

---

## 6) Executive summary (non-technical)

- The app already has a **solid foundation**: reusable layouts, service layer, and modular partial templates.
- The main challenge is **inconsistent adoption** across pages, especially older flows.
- A single, comprehensive standardization initiative can make pages feel and behave the same without rewriting everything.
- Best return on effort: **unify layout usage + list-page contract first**, then refactor a few large views.

---

## 7) Single comprehensive implementation plan (documented for execution)

### Task name

**Inventory UI Standardization Program (one coordinated project)**

### Goal in simple terms

Make every major page in the app feel and behave the same way, so users do not need to re-learn each screen and developers can build new pages faster with fewer one-off decisions.

### What this one project includes

This is **one single program of work** with multiple checkpoints, not many unrelated mini-projects:

1. **Unify page shells**
   - Move operational outlier pages that still use raw `_base` to the canonical component layouts (`create_manage_layout`, `form_layout`, `detail_layout`) unless they are intentionally special pages (login/error/help).

2. **Introduce one shared list-page contract**
   - Standardize query params (`q`, `status`, `active`, `sort`, `direction`, `page`, `page_size`, `view`).
   - Standardize required context keys (`page_obj`, `page_size`, `querystring`, `export_url`, `container_id`, `view`).
   - Require a `/table/` partial endpoint for all list modules and optional `/cards/` where appropriate.

3. **Refactor very large action-heavy views**
   - Keep one entry route, but split internal logic into clear action handlers (`receive`, `adjust`, `waste`, `transfer`, etc.) to reduce complexity and improve testability.

4. **Choose one default form interaction pattern**
   - Make HTMX-first the standard behavior for create/edit flows.
   - Keep legacy modal JSON handling only through a thin compatibility layer while pages migrate.

5. **Align detail-page behavior**
   - Apply a simple rule: read-mostly pages use `detail_layout`; edit-heavy pages use `form_layout`.
   - Review recipe detail and other edge pages against that rule.

6. **Add governance so the standard stays standard**
   - Publish a short “Page Blueprint Checklist” in docs.
   - Add smoke checks for list-page contract behavior (filters/sort/pagination/view).

### Delivery checkpoints

- **Checkpoint A (Foundation):** layout migration + published checklist.
- **Checkpoint B (Consistency):** list-page contract adopted across core list modules.
- **Checkpoint C (Maintainability):** large multi-action views refactored into handlers.
- **Checkpoint D (Stability):** smoke tests and regression checks in CI.

### Acceptance criteria (how we know this is done)

- All major user pages use a canonical layout or are explicitly documented exceptions.
- All major list pages accept and preserve the same filter/sort/pagination/view parameters.
- At least the highest-complexity operational flow(s) are split into action handlers with clearer tests.
- New page PRs include the blueprint checklist and pass list-page smoke checks where relevant.

### Expected user impact

- Cleaner and more predictable screens.
- Less confusion when moving between modules.
- Faster onboarding for new team members and fewer UI regressions over time.

---

## 8) Implementation status update (March 30, 2026)

Completed in this change set:

- Standardized stock take operational flow pages onto canonical layouts:
  - `stock_take_start` now uses `components/form_layout.html`.
  - `stock_take_count` now uses `components/detail_layout.html`.
  - `stock_take_review` now uses `components/detail_layout.html`.
- Standardized GRN create flow page onto canonical form layout:
  - `grns/create.html` now uses `components/form_layout.html` while preserving both select-PO and line-entry steps.
- Converted supplier cards template to a pure partial fragment:
  - `suppliers_card.html` no longer extends `_base`; it now behaves as an HTMX-rendered content fragment with pagination and toggle controls.

This implements the first practical slice of the standardization program by removing key `_base` outliers from operational workflows.
