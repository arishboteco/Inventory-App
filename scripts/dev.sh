#!/usr/bin/env bash
set -euo pipefail

# Start Django dev server and Tailwind/PostCSS watcher together.
# Stops both when this script exits.

trap 'kill 0' EXIT

python manage.py runserver 0.0.0.0:8000 &
npm run dev-css &

wait
