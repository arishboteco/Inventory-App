Agent Guide for Inventory-App

Purpose
- Provide fast, reliable context so an AI coding agent can work efficiently with minimal surprises.

Quickstart
- Python: 3.13+. Install deps: `make install`
- Node: 22+. Build CSS: `npm install && npm run build`
- DB + Migrations: `python manage.py migrate`
- Dev server + CSS watcher: `make dev` (runs Django + `npm run dev-css`)
- Tests (Python): `make test` or `pytest`
- Tests (JS): `npm test`
- Lint/Format: `make lint` and `make fmt`

Repo Layout
- Django app code: `inventory/`
- Django settings: `inventory_app/`
- Templates: `templates/`
- Static assets: `static/`
- Tests: `tests/` and `tests/frontend/`

Conventions
- Keep changes minimal and focused; do not rename files or symbols unless requested.
- Follow Black and Ruff; prefer `make fmt` and `make lint`.
- Reuse existing utilities/components (see `inventory/services/`, `templates/components/`).
- Update docs/templates/tests when changing behavior or UI.
- Prefer small, isolated patches; avoid broad refactors without direction.

Runtime Notes
- App serves on `:8000`. `make dev` starts both Django and the CSS watcher.
- Tailwind CSS is built via PostCSS (see `package.json` scripts).
- Environment variables: copy `env/dev.example` to `.env` for local dev.

Testing Guidance
- Start specific: run only impacted tests first (e.g., `pytest tests/test_items_table_accessibility.py`).
- Then broaden to `make test` before handoff.
- Frontend tests use Jest with jsdom.

CI Helpers
- `make ci` runs format, lint, and tests locally.
- Coverage: `make coverage` for a quick report.

What to Avoid
- Introducing new tooling unless necessary.
- Editing DB migrations without explicit instruction.
- Network-heavy actions during routine tasks (respect sandbox/approvals).

Troubleshooting
- CSS missing: run `npm run build`.
- Import errors: ensure `make install` completed and virtualenv/interpreter is correct.
- Port 8000 busy: `make up` will start or verify the dev server.

Contact Points
- Django views and services: `inventory/views/`, `inventory/services/`
- Forms: `inventory/forms/`
- Models: `inventory/models/`
- JS widgets: `static/js/`

