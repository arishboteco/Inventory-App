#!/usr/bin/env bash
# Lightweight UI contract checks (see templates/UI_CONTRACT_AND_CONFORMANCE.md).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "=== Raw gray utilities (inventory + components templates) ==="
rg -n "text-gray-|bg-gray-|border-gray-" templates/inventory templates/components || true
echo ""
echo "=== Filter forms (id=filters / hx-include) ==="
rg -n "id=\"filters\"|hx-include=\"#filters\"" templates/inventory || true
echo ""
echo "=== Inline button stacks (possible duplicate of components/button.html) ==="
rg -n "inline-flex items-center px-4 py-2" templates/inventory templates/components || true
