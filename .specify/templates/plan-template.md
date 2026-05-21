# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.13 (project target); Django 5.2  
**Primary Dependencies**: Django, HTMX, Alpine.js (where used), Tailwind (built static CSS), Plotly/Chart.js for charts  
**Storage**: PostgreSQL (production); SQLite optional locally per `AGENTS.md`  
**Testing**: pytest via `make test` / `make ci`  
**Target Platform**: Web (Linux/Render or local dev server)  
**Project Type**: Django monolith (templates + HTMX; no separate frontend build for core features)  
**Performance Goals**: [domain-specific, e.g., responsive lists/drawers for typical restaurant data volumes]  
**Constraints**: Decimal for money/qty; drawer/AJAX patterns; migrations must run on PostgreSQL in prod  
**Scale/Scope**: [feature-specific, e.g., single-tenant F&B operators, concurrent staff users]

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

Verify against `.specify/memory/constitution.md`: domain/status rules respected; Django + HTMX drawer patterns; JSON for drawer AJAX; `make ci` before done; `line_total` and formsets where applicable; nav registration if new URLs; no template Decimal math (use `@property`). Document any intentional violation in Complexity Tracking below.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

**Inventory Pro (Django)** — use this layout; extend with exact paths for this feature:

```text
inventory/                 # Main app: models, views, forms, migrations, templatetags, management
inventory_app/             # Project package: settings/, urls.py, navigation.py, wsgi/asgi
templates/                 # Django templates (pages, components, partials/drawers)
static/                    # Built CSS/JS (Tailwind output, vendor assets)
tests/                     # pytest tests (mirror domain areas as needed)
specs/<feature-branch>/    # This feature: spec.md, plan.md, tasks.md, research.md, etc.
Makefile                   # fmt, lint, test, ci
```

**Structure Decision**: [List the specific files you will add or change under `inventory/`, `inventory_app/`, `templates/`, `tests/`, and new migrations.]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation                  | Why Needed         | Simpler Alternative Rejected Because |
| -------------------------- | ------------------ | ------------------------------------ |
| [e.g., 4th project]        | [current need]     | [why 3 projects insufficient]        |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient]  |
