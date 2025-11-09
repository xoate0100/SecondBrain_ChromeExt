# Cursor Rules
- Read AI_SANDBOX_RULES.md and ACTIVE_PLAN.yaml at start.
- Never modify meta-framework paths.
- Always include `plan:<id> component:<component> task:<id>` in commit messages.
- Propose fixes until all pre-commit hooks pass, then commit autonomously.

## Commit Frequency (CRITICAL)
- **Commit incrementally**: Commit after completing each phase OR every 3-5 tasks
- **Use commit-checkpoint**: Run `python3 3_bootstrap_scripts/cli.py commit-checkpoint` for validated commits
- **Respect thresholds**: If >10 files changed, commit even if `auto_commit: false` (when `force_commit_on_checkpoint: true`)
- **Large changeset warning**: If >20 files changed since last commit, pre-commit will warn (consider committing sooner)
- **Never accumulate**: Don't wait until end of session - commit early and often
- **Reference**: See `docs/COMMIT_STRATEGY.md` for detailed commit frequency best practices

