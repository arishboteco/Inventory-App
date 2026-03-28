# Inventory Pro — AGENTS.md

## Cursor Cloud specific instructions

### Services overview

Inventory Pro is a single Django web app (no separate frontend build server). In dev mode you need:

| Service | Command | Notes |
|---------|---------|-------|
| Django dev server | `source .venv/bin/activate && python manage.py runserver 0.0.0.0:8000` | Main app on port 8000 |
| CSS watcher (optional) | `npm run dev-css` | Only needed when editing Tailwind CSS |

Or use `make dev` to start both together.

### Key dev commands

See `CLAUDE.md` for the full reference. Quick summary:

- `make ci` — format + lint + test (run before every commit)
- `make fmt` / `make lint` / `make test` — individual steps
- `npm test` — JavaScript tests (Jest)
- `npm run build` — build Tailwind CSS

### Database: SQLite in development

The app falls back to SQLite when `DATABASE_URL` is not set to a PostgreSQL URL. For local dev, set `DATABASE_URL=sqlite:///db.sqlite3` in `.env`.

**Critical gotcha:** Several inventory migrations (0004, 0007, 0030, 0032, 0033) contain raw PostgreSQL DDL (`DO $$ ... $$`, `CREATE EXTENSION`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`). These fail on SQLite. The correct approach for local SQLite dev:

1. Apply non-inventory migrations normally: `python manage.py migrate admin auth contenttypes sessions django_q`
2. Fake all inventory migrations: `python manage.py migrate --fake inventory`
3. Create inventory tables from ORM models using `schema_editor.create_model()`

The test settings (`inventory_app.settings.test`) already handle this by setting `MIGRATION_MODULES = {"inventory": None}` and using `:memory:` SQLite.

### Auto-created admin user

The `core/apps.py` post_migrate signal auto-creates an `admin` / `admin` superuser. This signal fires on every `migrate` command and can fail if `auth_user` table doesn't exist yet (e.g. when migrating `contenttypes` first). The workaround is to apply auth-dependent migrations before inventory migrations.

### Pre-existing test failures

28 of 189 Python tests fail due to pre-existing issues (stale template assertions, removed imports like `RecipeComponent` and `_stock_trend_data`). These are not caused by environment setup. The 161 passing tests confirm the test framework works correctly.

### Environment variables

Minimum `.env` for local dev:
```
DJANGO_SECRET_KEY=<any-random-string>
DATABASE_URL=sqlite:///db.sqlite3
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DISABLE_KEEP_ALIVE=true
DJANGO_SETTINGS_MODULE=inventory_app.settings.dev
```

### Python version

The project targets Python 3.13 (`pyproject.toml` has `target-version = ["py313"]`). Install from the `deadsnakes` PPA if not available: `sudo apt-get install python3.13 python3.13-venv python3.13-dev`.
