#!/usr/bin/env bash
set -euo pipefail

# Commit message validator
# Validates that commit messages include required format: plan:<plan_id> component:<component> task:<id>
# Reference: AI_SANDBOX_RULES.md - "Every commit message MUST include: plan:<plan_id> component:<component> task:<id>"

# Pre-commit passes commit message file as first argument
# If not provided, try to get from git
COMMIT_MSG_FILE="${1:-}"

# Check if commit message file exists
if [ ! -f "$COMMIT_MSG_FILE" ]; then
  # If no commit message file, try to get from git
  COMMIT_MSG=$(git log -1 --pretty=%B 2>/dev/null || echo "")
else
  COMMIT_MSG=$(cat "$COMMIT_MSG_FILE" 2>/dev/null || echo "")
fi

# If still no message, allow (might be initial commit or merge)
if [ -z "$COMMIT_MSG" ]; then
  echo "[commit-validator] ⚠️  No commit message found, allowing (may be initial commit)"
  exit 0
fi

# Required format: plan:<plan_id> component:<component> task:<id>
# Component must be: frontend, backend, or shared
# Task must be a number
REQUIRED_PATTERN="plan:[a-zA-Z0-9_-]+ component:(frontend|backend|shared) task:[0-9]+"

# Check if commit message matches required format
if echo "$COMMIT_MSG" | grep -qE "$REQUIRED_PATTERN"; then
  echo "[commit-validator] ✅ Commit message format valid"
  exit 0
fi

# Check for merge commits, revert commits, or other special cases
if echo "$COMMIT_MSG" | grep -qE "^(Merge|Revert|fixup!|squash!)"; then
  echo "[commit-validator] ⚠️  Special commit type detected, skipping validation"
  exit 0
fi

# Validation failed
echo "[commit-validator] ❌ Commit message format invalid"
echo ""
echo "Required format: plan:<plan_id> component:<component> task:<id>"
echo ""
echo "Example:"
echo "  plan:chrome-extension-mvp-init component:frontend task:1"
echo ""
echo "Your commit message:"
echo "  $COMMIT_MSG" | head -n 1
echo ""
echo "Reference: 0_phase0_bootstrap/AI_SANDBOX_RULES.md"
exit 1
