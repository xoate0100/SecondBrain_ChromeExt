#!/usr/bin/env bash
set -euo pipefail
STATUS=0

# Exclude patterns for security scan
EXCLUDE_PATTERNS=":!*.md :!node_modules/* :!dist/* :!coverage/* :!*.min.js :!*.min.css :!package-lock.json :!yarn.lock :!pnpm-lock.yaml"

echo "[security] Scanning for secrets and security vulnerabilities..."

# 1. Secrets scan (basic): grep common patterns; replace with gitleaks if available.
if git grep -nE "(AWS_SECRET|BEGIN RSA PRIVATE KEY|password\s*=|api_key\s*=)" -- . $EXCLUDE_PATTERNS 2>/dev/null; then
  echo "[security] ❌ Secret-like patterns found."
  STATUS=1
fi

# 2. Eval/exec detection (from SECURITY_BASELINES.md)
# Only check for actual function calls, not variable names or comments
echo "[security] Checking for eval/exec usage..."
EVAL_MATCHES=$(git grep -nE "(^|[^a-zA-Z_])eval\s*\(|(^|[^a-zA-Z_])exec\s*\(|new\s+Function\s*\(" -- . $EXCLUDE_PATTERNS 2>/dev/null | grep -vE "(exec_mode|execution|executable|#.*exec|#.*eval|Execution_Mode)" | grep -vE "\.(md|txt|yml|yaml)$" || true)
if [ -n "$EVAL_MATCHES" ]; then
  echo "[security] ERROR: Dangerous eval/exec patterns found."
  echo "[security]   Security baseline: Disallow eval/exec, command injections, insecure deserialization"
  echo "$EVAL_MATCHES"
  STATUS=1
fi

# 3. Command injection detection
# Only check for actual function calls, not variable names or comments
echo "[security] Checking for command injection patterns..."
CMD_INJECT_MATCHES=$(git grep -nE "(child_process\.|\.spawn\s*\(|\.exec\s*\(|system\s*\(|popen\s*\(|os\.system|subprocess\.(call|Popen)\s*\()" -- . $EXCLUDE_PATTERNS 2>/dev/null | grep -vE "(exec_mode|execution|executable|#.*exec|#.*spawn|Execution_Mode)" | grep -vE "\.(md|txt|yml|yaml)$" || true)
if [ -n "$CMD_INJECT_MATCHES" ]; then
  echo "[security] ERROR: Command injection patterns found."
  echo "[security]   Security baseline: Disallow command injections"
  echo "$CMD_INJECT_MATCHES"
  STATUS=1
fi

# 4. Insecure deserialization detection
echo "[security] Checking for insecure deserialization..."
if git grep -nE "(pickle\.load|pickle\.loads|yaml\.load|yaml\.unsafe_load|marshal\.load|eval\(.*json)" -- . $EXCLUDE_PATTERNS 2>/dev/null; then
  echo "[security] ❌ Insecure deserialization patterns found."
  echo "[security]   Security baseline: Disallow insecure deserialization"
  STATUS=1
fi

# 5. Node audit (best-effort)
if [ -f "frontend/package.json" ]; then
  echo "[security] Running npm audit..."
  if (cd frontend && npm audit --audit-level=high 2>/dev/null); then
    echo "[security] ✅ npm audit passed"
  else
    echo "[security] ⚠️  npm audit found vulnerabilities (non-blocking)"
    # Don't fail on npm audit for now, but warn
  fi
fi

# 6. Python dependency check (if requirements.txt exists)
if [ -f "requirements.txt" ] || [ -f "backend/requirements.txt" ]; then
  echo "[security] Checking Python dependencies..."
  # Check for known vulnerable packages (basic check)
  if git grep -nE "(django<2|flask<1|requests<2)" -- requirements.txt backend/requirements.txt 2>/dev/null; then
    echo "[security] ⚠️  Potentially outdated Python dependencies found"
    # Non-blocking warning
  fi
fi

if [ $STATUS -eq 0 ]; then
  echo "[security] OK: Security scan passed"
else
  echo "[security] ERROR: Security scan failed - fix issues before committing"
fi

exit $STATUS
