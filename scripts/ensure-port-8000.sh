#!/usr/bin/env bash
set -euo pipefail

PORT=${1:-8000}
# Allow override via env var; default to local .venv if present
PY=${PYTHON_BIN:-}
if [ -z "${PY}" ]; then
  if [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
  else
    PY="python3"
  fi
fi

if lsof -i :"$PORT" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  echo "Port $PORT already listening."
  exit 0
fi

echo "Starting Django dev server on 0.0.0.0:${PORT}..."
nohup "$PY" manage.py runserver 0.0.0.0:"$PORT" >/tmp/django_${PORT}.log 2>&1 &
PID=$!
echo $PID > /tmp/django_${PORT}.pid
echo "Started PID $PID. Logs: /tmp/django_${PORT}.log"

# Wait until port is listening (max ~10s)
for i in {1..40}; do
  if lsof -i :"$PORT" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
    echo "Port $PORT is ready."
    exit 0
  fi
  sleep 0.25
done

echo "Warning: Port $PORT not ready yet after waiting. Check logs at /tmp/django_${PORT}.log"
exit 1
