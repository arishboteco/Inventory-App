# Inventory Pro — Production Readiness Roadmap

**Generated:** 2026-03-25
**App:** Django F&B inventory management (Indents → POs → GRN → Stock)
**Users:** Internal restaurant/café operations team (~5–20 staff)
**Hosting:** Render.com (PostgreSQL on Supabase)
**Live URL:** https://inventory-app-kguo.onrender.com/

---

## Current State Summary

| Dimension | Status | Key Finding |
|-----------|--------|-------------|
| Core Workflow Integrity | ⚠️ Functional but fragile | Silent failures in indent, PO, stock-take flows |
| Data Integrity | ⚠️ Mostly OK | Some forms accept invalid/empty data silently |
| UX Clarity | ⚠️ Needs polish | Hardcoded user list in filter, confusing table/cards nav |
| Domain Feature Completeness | 🔴 Gaps | No food cost report, no recipe costing export, stock-take has no freeze |
| Operational Readiness | 🔴 CRITICAL | **50+ view endpoints have zero authentication protection** |

---

## Phase A — Fix the Authentication Gap *(Production Blocker)*

> **Gate:** Every UI endpoint redirects unauthenticated requests to `/accounts/login/`. No data is accessible without a valid session.

This is the single most important thing to fix before real users touch the app. Currently ~50 view functions and class-based views are missing `@login_required` or `LoginRequiredMixin`, meaning anyone with the URL can read (and in some cases write) all data.

| Step | Task | File(s) | Effort |
|------|------|---------|--------|
| A1 | Add `LoginRequiredMixin` to all CBVs in `indents.py` | `views/indents.py` | 30 min |
| A2 | Add `@login_required` to all FBVs in `indents.py` | `views/indents.py` | 30 min |
| A3 | Add auth to all views in `stock_take.py` | `views/stock_take.py` | 30 min |
| A4 | Add auth to all views in `purchase_orders.py` | `views/purchase_orders.py` | 30 min |
| A5 | Add auth to all views in `goods_received.py` | `views/goods_received.py` | 30 min |
| A6 | Add auth to all views in `recipes.py` | `views/recipes.py` | 30 min |
| A7 | Add auth to all views in `suppliers.py` | `views/suppliers.py` | 15 min |
| A8 | Add auth to all views in `stock.py` (movements, history) | `views/stock.py` | 30 min |
| A9 | Add auth to `explore.py`, `visualizations.py`, `ml.py`, `what_if.py` | 4 files | 30 min |
| A10 | Smoke-test: open each major URL in an incognito window and verify redirect | — | 30 min |

**Risk flag:** A global middleware (`LOGIN_REQUIRED_MIDDLEWARE`) could replace steps A1–A9 in one change — but needs care to whitelist the login page itself and any public endpoints (e.g., health check).

---

## Phase B — Fix Silent Failures & Error Handling

> **Gate:** No workflow fails silently. Every invalid input or backend error produces visible, actionable user feedback.

| Step | Task | File | Line(s) | Effort |
|------|------|------|---------|--------|
| B1 | Stock-take count: replace silent `except ValueError: pass` with form error display | `views/stock_take.py` | 113–119 | 1 hr |
| B2 | Indent update: log + toast instead of bare `except: pass` on department lookup | `views/indents.py` | 801–816 | 1 hr |
| B3 | Indent consolidation: validate all selected indents are APPROVED before consolidating | `views/indents.py` | 1085 | 1 hr |
| B4 | PO receive: reject negative quantities instead of silently converting to 0 | `views/purchase_orders.py` | 679–680 | 30 min |
| B5 | GRN adhoc: validate at least one line item exists before creating GRN | `views/goods_received.py` | 545–547 | 30 min |
| B6 | CSV upload (suppliers): add encoding fallback (`utf-8-sig`, `latin-1`) and file-size guard | `views/suppliers.py` | 92 | 1 hr |
| B7 | Recipe create: enforce circular-dependency check in `recipe_create()` view (it's only in `RecipeItem.clean()`) | `views/recipes.py` | 260–309 | 1 hr |

---

## Phase C — Remove UX Confusion

> **Gate:** A new team member can navigate the full indent → PO → GRN → stock flow without asking questions.

| Step | Task | File | Effort |
|------|------|------|--------|
| C1 | Replace hardcoded `["admin", "testuser"]` user list in indent filter with a DB query of active users | `templates/inventory/indents_list.html:73` | 30 min |
| C2 | Remove `/purchase-orders/table/` and `/purchase-orders/cards/` from the nav — only expose the unified list view | `urls.py` + sidebar template | 30 min |
| C3 | Same as C2 for `/indents/table/` and `/items/table/` — table views should be HTMX-internal only, not nav items | sidebar template | 30 min |
| C4 | Add the Workflow Guide (`/guides/workflow/`) link to the sidebar — it exists but is undiscoverable | sidebar template | 15 min |
| C5 | Stock-take: show a clear "incomplete items" warning on the review page before allowing Confirm | `templates/inventory/stock_take/` | 1 hr |
| C6 | PO receive form: show "ordered qty" next to each line so staff know the upper limit | `templates/inventory/purchase_orders/` | 1 hr |

---

## Phase D — Add Missing Domain Features

> **Gate:** The app covers the standard F&B inventory management feature set for a single-site operation.

| Step | Task | Priority | Effort |
|------|------|----------|--------|
| D1 | **Food cost report** — per-recipe table: total cost, selling price, actual food cost %, traffic-light status | Critical | 1–2 days |
| D2 | **Recipe costing export** — PDF/CSV export of recipe card with ingredient costs | High | 1 day |
| D3 | **Stock take: freeze period** — lock items from other stock movements while a take is In Progress | High | 1–2 days |
| D4 | **Stock take: auto-adjust on confirm** — create ADJUSTMENT stock movements from variances automatically | High | 1 day |
| D5 | **Inventory valuation report** — total stock value = current_stock × last_purchase_price per item | High | 4 hrs |
| D6 | **Supplier performance metrics** — on-time delivery %, average lead time, price variance per supplier | Medium | 1–2 days |
| D7 | **Low stock trend** — items approaching reorder point, trend sparkline over last 30 days | Medium | 1 day |
| D8 | **Batch indent approval** — approve multiple submitted indents in one action from the list | Medium | 4 hrs |
| D9 | **Waste reason codes** — extend WASTAGE stock movement with a reason (Spoilage / Expiry / Dropped / Over-prep) | Medium | 4 hrs |

---

## Phase E — Data Quality & Reporting

> **Gate:** Managers can answer "how are we doing?" from the app alone, without exporting to spreadsheets.

| Step | Task | Effort |
|------|------|--------|
| E1 | Dashboard KPI widgets: weekly spend, top 5 wasted items, stock health score | 1–2 days |
| E2 | Period-over-period comparison in History Reports (this week vs last week) | 1 day |
| E3 | GRN discrepancy summary report — aggregate over/under deliveries by supplier | 4 hrs |
| E4 | ML forecast confidence intervals + minimum data-point guard (raise from 2 → 8 data points) | 4 hrs |
| E5 | ABC classification report — list all A/B/C items with consumption value | 4 hrs |

---

## Phase F — Scale & Operational Readiness

> **Gate:** App handles expected load, secrets are managed properly, and on-call knows when something breaks.

| Step | Task | Effort |
|------|------|--------|
| F1 | Add Sentry (or similar) for error monitoring — currently errors are invisible in production | 2 hrs |
| F2 | Add health-check endpoint (`/health/`) for Render uptime monitoring | 30 min |
| F3 | Rotate `SECRET_KEY` and store all secrets in Render environment variables (not `.env` in repo) | 1 hr |
| F4 | Add `select_related` / `prefetch_related` to the worst N+1 queries (indents list, GRN list) | 1–2 days |
| F5 | Multi-user: add role-based permissions (Manager vs Kitchen Staff vs Viewer) | 2–3 days |
| F6 | Automated DB backups — verify Supabase point-in-time recovery is enabled | 1 hr |

---

## Recommended Sprint Order

```
Week 1:  Phase A (auth) — non-negotiable before any real users
Week 2:  Phase B (silent failures) + Phase C (UX polish)
Week 3:  Phase D, steps D1–D5 (core reporting + stock-take improvements)
Week 4:  Phase D, steps D6–D9 + Phase E
Ongoing: Phase F items as capacity allows
```

---

## Quick Wins (< 1 hour each, high visibility)

1. **A1–A9** — auth protection (mechanical, low risk, massive security improvement)
2. **C1** — replace hardcoded user list (one DB query change)
3. **C4** — add workflow guide to nav (one template line)
4. **B4** — reject negative PO quantities (one-line validation)
5. **F2** — health-check endpoint (5 lines of code)
