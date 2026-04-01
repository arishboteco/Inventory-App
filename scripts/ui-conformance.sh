#!/usr/bin/env bash
# Lightweight UI contract checks (see templates/UI_CONTRACT_AND_CONFORMANCE.md).
# Default: report-only (always exits 0). Pass --fail to gate CI.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FAIL_MODE=false
if [[ "${1:-}" == "--fail" ]]; then
  FAIL_MODE=true
fi

exit_code=0

echo "=== Raw gray utilities (inventory + components templates) ==="
if rg -n "text-gray-|bg-gray-|border-gray-" templates/inventory templates/components; then
  echo "FAIL: Found raw gray utility classes"
  exit_code=1
else
  echo "PASS: No raw gray utility classes found"
fi
echo ""

echo "=== Filter forms (id=filters / hx-include) ==="
if rg -n "id=\"filters\"|hx-include=\"#filters\"" templates/inventory; then
  echo "INFO: Filter form references found (expected)"
else
  echo "WARN: No filter form references found"
fi
echo ""

echo "=== Inline button stacks (possible duplicate of components/button.html) ==="
if rg -n "inline-flex items-center px-4 py-2" templates/inventory templates/components; then
  echo "INFO: Inline button stacks found (review for component reuse)"
else
  echo "PASS: No inline button stacks found"
fi
echo ""

if $FAIL_MODE; then
  if [[ $exit_code -ne 0 ]]; then
    echo "UI conformance check FAILED"
    exit 1
  fi
  echo "UI conformance check PASSED"
fi
exit 0
