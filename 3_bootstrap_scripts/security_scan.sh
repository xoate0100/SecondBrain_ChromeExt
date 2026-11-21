#!/usr/bin/env bash
set -euo pipefail
STATUS=0
# Exclude scanner definition files so the pattern literals do not self-hit.
if git grep -nE "(AWS_SECRET|BEGIN RSA PRIVATE KEY|password[[:space:]]*=|api_key[[:space:]]*=)" -- . \
  ':!*.md' \
  ':!3_bootstrap_scripts/security_scan.sh' \
  ':!3_bootstrap_scripts/security_scan.py' \
  ':!**/security_scan.sh' \
  ':!**/security_scan.py' ; then
  echo "Secret-like patterns found."
  STATUS=1
fi
if [ -f "frontend/package.json" ]; then
  (cd frontend && npm audit --audit-level=high || true)
fi
exit $STATUS
