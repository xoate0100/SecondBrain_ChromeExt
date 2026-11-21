#!/usr/bin/env bash
set -euo pipefail
STATUS=0
backend_has_python() {
  [ -d "backend" ] || return 1
  find backend -type f \( -name "*.py" -o -name "*.pyi" \) ! -path "*/.*" 2>/dev/null | grep -q .
}
if backend_has_python; then
  python3 -m pip install --quiet flake8 mypy || true
  (cd backend && flake8 .) || STATUS=1
  (cd backend && mypy .) || STATUS=1
else
  echo "[static-analysis] skip: no Python files under backend/"
fi
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
  (cd frontend && npm ci --silent && npm run -s typecheck || npm run -s build --if-present) || STATUS=1
fi
exit $STATUS
