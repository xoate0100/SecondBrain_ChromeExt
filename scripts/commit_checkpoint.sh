#!/bin/bash
# Commit Checkpoint Script
# Validates staged files, runs pre-commit hooks, and commits with proper message format
# Usage: bash scripts/commit_checkpoint.sh [optional commit message]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "[commit-checkpoint] Starting commit checkpoint process..."

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}[commit-checkpoint] Error: Not in a git repository${NC}"
    exit 1
fi

# Check if there are staged files
if [ -z "$(git diff --cached --name-only)" ]; then
    echo -e "${YELLOW}[commit-checkpoint] Warning: No staged files. Nothing to commit.${NC}"
    exit 0
fi

# Get staged files count
STAGED_COUNT=$(git diff --cached --name-only | wc -l | tr -d ' ')
echo "[commit-checkpoint] Found $STAGED_COUNT staged file(s)"

# Load active plan if it exists
PLAN_FILE="6_ai_runtime_context/ACTIVE_PLAN.yaml"
if [ -f "$PLAN_FILE" ]; then
    # Extract plan info using Python (if available) or basic parsing
    if command -v python3 &> /dev/null; then
        PLAN_ID=$(python3 -c "import yaml, sys; print(yaml.safe_load(open('$PLAN_FILE')).get('plan_id', 'unknown'))" 2>/dev/null || echo "unknown")
        COMPONENT=$(python3 -c "import yaml, sys; print(yaml.safe_load(open('$PLAN_FILE')).get('component', 'shared'))" 2>/dev/null || echo "shared")
    else
        PLAN_ID="unknown"
        COMPONENT="shared"
    fi
else
    PLAN_ID="unknown"
    COMPONENT="shared"
fi

# Get current task from pointer if available
TASK_FILE="6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml"
if [ -f "$TASK_FILE" ] && command -v python3 &> /dev/null; then
    TASK_ID=$(python3 -c "import yaml, sys; print(yaml.safe_load(open('$TASK_FILE')).get('current_task', 1))" 2>/dev/null || echo "1")
else
    TASK_ID="1"
fi

# Run pre-commit hooks
echo "[commit-checkpoint] Running pre-commit hooks..."
if command -v pre-commit &> /dev/null; then
    if ! pre-commit run --hook-stage commit 2>&1; then
        echo -e "${RED}[commit-checkpoint] Error: Pre-commit hooks failed. Fix issues before committing.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}[commit-checkpoint] Warning: pre-commit not installed. Skipping hook validation.${NC}"
fi

# Generate commit message
if [ -n "$1" ]; then
    # Use provided message, but ensure it includes plan/task tags
    COMMIT_MSG="$1"
    if [[ "$COMMIT_MSG" != *"plan:"* ]] && [[ "$COMMIT_MSG" != *"task:"* ]]; then
        COMMIT_MSG="$COMMIT_MSG

plan:$PLAN_ID component:$COMPONENT task:$TASK_ID"
    fi
else
    # Generate default message
    COMMIT_MSG="feat: checkpoint commit

plan:$PLAN_ID component:$COMPONENT task:$TASK_ID"
fi

# Commit
echo "[commit-checkpoint] Committing with message..."
echo "[commit-checkpoint] Message: $COMMIT_MSG"
if git commit -m "$COMMIT_MSG"; then
    echo -e "${GREEN}[commit-checkpoint] ✅ Commit successful${NC}"
    echo "[commit-checkpoint] Commit hash: $(git rev-parse --short HEAD)"
else
    echo -e "${RED}[commit-checkpoint] Error: Commit failed${NC}"
    exit 1
fi

