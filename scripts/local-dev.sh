#!/usr/bin/env bash
# local-dev.sh — start local development environment
# Usage: bash scripts/local-dev.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Load .env to override any shell-level DATABASE_URL etc.
if [ -f ".env" ]; then
  set -a
  source .env
  set +a
  echo "✓ Loaded .env"
fi

# Start Postgres if not running
if ! pg_lsclusters | grep -q "online"; then
  echo "Starting PostgreSQL..."
  pg_ctlcluster 16 main start
fi
echo "✓ PostgreSQL running"

# Run any pending migrations
python manage.py migrate --run-syncdb 2>/dev/null || python manage.py migrate
echo "✓ Migrations up to date"

# Start server + CSS watcher
echo "Starting server at http://localhost:8000 (login: admin / admin123!)"
python manage.py runserver 0.0.0.0:8000 &
npm run dev-css &

trap 'kill 0' EXIT
wait
