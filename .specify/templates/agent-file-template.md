# Inventory Pro Development Guidelines

Auto-generated from feature plans; baseline below reflects the current monolith. Last updated: [DATE]

## Active Technologies

- **Backend**: Django 5.2, Python 3.13 target
- **UI**: Django templates, HTMX, Alpine.js (selective), Tailwind utility classes (built CSS)
- **Data**: PostgreSQL (production); SQLite optional for local dev (`AGENTS.md`)
- **Charts**: Plotly, Chart.js (existing dashboards)
- **Quality**: Black, Ruff, pytest — `make ci` before merge

## Project Structure

```text
inventory/              # Models, views, forms, migrations, templatetags
inventory_app/          # settings/, urls.py, navigation.py
templates/              # Pages, components, HTMX partials / drawers
static/                 # Compiled CSS/JS and static assets
tests/                  # Pytest
specs/                  # Spec Kit per-feature artifacts
```

## Commands

| Command | Purpose |
|--------|---------|
| `make ci` | Format (Black), lint (Ruff), test (pytest) — run before commit |
| `make fmt` / `make lint` / `make test` | Individual steps |
| `make dev` | Django + optional CSS watcher (`AGENTS.md`) |

## Code Style

- **Money / quantities**: `Decimal`, not `float`
- **Drawers**: `fetch()` or `hx-post`; JSON `JsonResponse` for AJAX; no raw form POST to partials
- **Templates**: No Decimal math — add `@property` on models
- **URLs**: `snake_case` names (`indent_list`, `po_create_partial`, …)
- **Nav**: `inventory_app/navigation.py` + `templates/components/top_nav.html` for new items
- **Partials**: HTML comments only (`<!-- -->`) where fragments may render standalone

## Recent Changes

[LAST 3 FEATURES AND WHAT THEY ADDED]

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
