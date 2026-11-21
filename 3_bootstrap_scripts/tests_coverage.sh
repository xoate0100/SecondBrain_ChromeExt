#!/usr/bin/env bash
set -euo pipefail
STATUS=0
backend_has_python() {
  [ -d "backend" ] || return 1
  find backend -type f \( -name "*.py" -o -name "*.pyi" \) ! -path "*/.*" 2>/dev/null | grep -q .
}
if backend_has_python; then
  python3 -m pip install --quiet pytest pytest-cov || true
  if ! pytest -q --cov=backend --cov-report=term-missing; then
    STATUS=1
  fi
else
  echo "[tests-coverage] skip: no Python files under backend/"
fi
if [ -f "frontend/package.json" ]; then
  if ! (cd frontend && npm ci --silent && npm test --silent -- --coverage); then
    # If no test script, do not fail the gate for placeholder frontends
    if npm --prefix frontend run | grep -q " test"; then
      STATUS=1
    else
      echo "[tests-coverage] skip: frontend has no test script"
    fi
  fi
fi
exit $STATUS
