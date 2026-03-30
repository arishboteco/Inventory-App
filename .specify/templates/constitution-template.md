# Inventory Pro Constitution

Governing principles for spec-driven work on this codebase. Complements `CLAUDE.md` and `AGENTS.md` for day-to-day details.

## Core Principles

### I. Domain integrity

Features MUST respect existing procurement and stock semantics unless the spec explicitly changes them: Indents → Purchase Orders → GRNs → Stock movements; Recipes (including sub-recipes); Stock takes and adjustments. Use `Decimal` for money and quantities. Preserve status flows (Indent, PO, GRN, Stock take) and status-conditional UI—no “show every action” drawers.

### II. Django-first, server-rendered UI

The app is Django 5.2 with templates, HTMX, Alpine.js where needed, and Tailwind utilities. No new SPA or separate frontend repo for features unless the constitution is formally amended. New pages and partials live under `templates/`; styles follow existing Tailwind patterns.

### III. HTMX drawer and AJAX contracts

Create/edit flows that use the drawer pattern MUST load via `data-modal-url` / HTMX and submit with `fetch()` or `hx-post`—never raw form POST to a partial URL. AJAX create/update views MUST return JSON for XMLHttpRequest clients (e.g. `JsonResponse({'ok': True, 'id': ...})`). Do not use `form.submit()` inside drawers.

### IV. Quality gate before merge

Before a feature is considered done, run `make ci` (Black, Ruff, pytest). New logic SHOULD have tests when behavior is non-trivial or regression-prone (models, views, stock/PO/GRN math). Follow URL naming (`<module>_<action>`), register nav in `inventory_app/navigation.py` and icons in `templates/components/top_nav.html` when adding routes.

### V. Simplicity and traceability

Prefer extending existing models, views, and templates over new layers unless justified in the plan’s Complexity Tracking. Specifications and plans MUST name affected apps (`inventory`, `inventory_app`), templates, and migrations when relevant. Avoid Decimal arithmetic in templates—use model `@property` helpers.

## Technology and constraints

- **Stack**: Python 3.13 (project target), Django 5.2, PostgreSQL in production; SQLite possible for local dev per `AGENTS.md`.
- **Forms**: Include formset management fields where line items exist (PO, recipes). `PurchaseOrderItem.line_total` MUST be set (`quantity_ordered × unit_price`) before save.
- **Comments in partials**: Use HTML comments (`<!-- -->`), not `{# #}`, in fragments that may render outside full template context.
- **Deployment**: Render; optional keep-alive in `inventory/apps.py`—do not break startup if env flags disable it.

## Workflow and collaboration

- Feature branches: `feature/<short-slug>` from the team’s integration branch (e.g. `feature/django-refactor`); PR title `<verb>: <what changed>`.
- Spec Kit artifacts for a feature live under `specs/<branch-folder>/` as produced by `/speckit.*` commands.
- Plans MUST include a Constitution Check section and call out violations with rationale in Complexity Tracking.
- Ambiguous requirements SHOULD be resolved with `/speckit.clarify` before `/speckit.plan`.

## Governance

This constitution overrides ad-hoc shortcuts for features started under Spec Kit. Changes here should be deliberate: update version and “Last Amended”, and align `CLAUDE.md` if operational guidance shifts. Runtime coding habits (HTMX, drawers, Decimal, nav) remain non-negotiable unless amended here.

**Version**: 1.0.0 | **Ratified**: 2026-03-30 | **Last Amended**: 2026-03-30
