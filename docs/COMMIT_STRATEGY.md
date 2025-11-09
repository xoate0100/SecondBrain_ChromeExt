# Commit Strategy - Best Practices

## Overview

This document defines the commit strategy for projects initialized from the meta-framework template. The goal is to enforce incremental commits that prevent large uncommitted changesets and ensure code quality gates are validated early.

## Commit Frequency

### Default Strategy: Checkpoint-Based

The default commit strategy is `checkpoint_based`, which commits when specific thresholds are met:

- **After completing each phase** (logical task group)
- **After N tasks complete** (default: 5 tasks)
- **When file count threshold exceeded** (default: 10 files changed)

### Commit Frequency Options

Projects can configure commit frequency via `ACTIVE_PLAN.yaml`:

- **`per_task`**: Commit after each task completes
- **`per_phase`**: Commit after completing logical task groups
- **`checkpoint_based`**: Use commit checkpoints (default, recommended)
- **`manual`**: No automatic commits (requires explicit commit commands)

## Commit Checkpoints

Commit checkpoints provide a safety mechanism to ensure incremental commits even when `auto_commit: false` is set.

### Configuration

```yaml
commit_checkpoints:
  after_phases: true  # Commit after completing each phase
  after_task_count: 5  # Commit after N tasks complete
  after_file_threshold: 10  # Commit when N files changed
  force_commit_on_checkpoint: true  # Override auto_commit: false
```

### How It Works

1. **After Phases**: When a logical task group (phase) is completed, commit if `after_phases: true`
2. **After Task Count**: When `after_task_count` tasks are completed, commit regardless of `auto_commit` setting (if `force_commit_on_checkpoint: true`)
3. **File Threshold**: When `after_file_threshold` files are changed since last commit, commit (if `force_commit_on_checkpoint: true`)

### Relationship to `auto_commit`

- If `auto_commit: true`: Normal commits happen automatically
- If `auto_commit: false`: 
  - If `force_commit_on_checkpoint: true`: Checkpoints override `auto_commit` and force commits
  - If `force_commit_on_checkpoint: false`: Checkpoints are ignored, no automatic commits

## Commit Message Format

**MANDATORY**: All commit messages must include plan, component, and task information:

```
<description>

plan:<plan_id> component:<component> task:<task_id>
```

### Examples

```
feat: add user authentication module

plan:auth-setup component:backend task:1
```

```
fix: resolve TDD violation in payment processor

plan:payment-integration component:backend task:5
```

## When to Commit

### Required Triggers

1. **After completing each phase** (logical task group)
2. **Every 3-5 tasks** (configurable via `after_task_count`)
3. **When file threshold exceeded** (default: 10 files, configurable via `after_file_threshold`)
4. **When completing logical unit of work** (feature, module, component)

### Large Changeset Warning

A pre-commit hook warns (non-blocking) if >20 files changed since last commit. This indicates:
- Potential need for earlier commits
- Risk of building on unvalidated foundation
- Difficulty in debugging if issues arise

## Using Commit Checkpoint Script

### Manual Usage

```bash
# Use default message format
bash scripts/commit_checkpoint.sh

# Use custom message (will still add plan/task tags if missing)
bash scripts/commit_checkpoint.sh "feat: implement user login"
```

### Via CLI

```bash
python3 3_bootstrap_scripts/cli.py commit-checkpoint
```

### What It Does

1. Validates staged files
2. Runs pre-commit hooks (TDD, SOLID, lint, etc.)
3. Generates commit message with plan/task tags
4. Commits with proper format
5. Reports commit hash on success

## Best Practices

### For AI Agents (Cursor)

1. **Commit Incrementally**: Don't wait until end of session to commit
2. **Respect Checkpoints**: Commit when thresholds are met
3. **Follow TDD**: Tests must be included in same commit as code
4. **Validate Early**: Pre-commit hooks catch issues early
5. **Use Checkpoint Script**: Use `commit-checkpoint` command for consistent commits

### For Human Developers

1. **Commit Often**: Small, focused commits are easier to review and debug
2. **Test Before Commit**: Ensure all tests pass before committing
3. **Follow Message Format**: Always include plan/component/task tags
4. **Monitor Changeset Size**: Keep commits under 20 files when possible
5. **Use Checkpoint Script**: Ensures consistent commit format and validation

## Troubleshooting

### Pre-commit Hooks Fail

If pre-commit hooks fail:
1. Fix the issues (TDD violations, SOLID violations, lint errors, etc.)
2. Re-run: `pre-commit run --all-files`
3. Stage fixes and commit again

### Large Uncommitted Changeset

If you have >20 files uncommitted:
1. Review changes and identify logical groups
2. Commit in phases (e.g., commit config files, then components, then tests)
3. Use `commit-checkpoint` script to ensure proper format

### `auto_commit: false` But Want Commits

If `auto_commit: false` but you want commits:
1. Set `commit_checkpoints.force_commit_on_checkpoint: true`
2. Or manually use `commit-checkpoint` script
3. Or temporarily set `auto_commit: true`

## References

- **AI Sandbox Rules**: `0_phase0_bootstrap/AI_SANDBOX_RULES.md`
- **TDD Guide**: `1_global_standards/TEST_STRATEGY_TDD.md`
- **SOLID Principles**: `1_global_standards/SOLID_PRINCIPLES.md`

