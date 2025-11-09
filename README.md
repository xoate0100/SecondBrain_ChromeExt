# Master Git Meta-Framework (L2.5 Single-Agent Sandbox)

## Use

### Initial Setup (One Time)

1. **Customize MVP Specification** (optional but recommended):
   - Edit `0_phase0_bootstrap/MVP_SPECIFICATION.yaml` with your project details

2. **Run initialization**:
   ```bash
   python3 3_bootstrap_scripts/cli.py init
   ```

3. **Review generated plan**:
   - Check `6_ai_runtime_context/ACTIVE_PLAN.yaml`
   - Modify if needed

### Development Workflow

4. In Cursor, open `0_phase0_bootstrap/AI_SANDBOX_RULES.md` and run your plan
5. The agent commits autonomously when all hooks pass, then open a PR

See `INITIALIZATION_GUIDE.md` for detailed instructions.

## Multi-Component
- frontend/, backend/, shared/ with per-component routing and thresholds.
- Architecture boundaries enforced via `5_reference_architectures/LAYER_RULES.yaml`.

## Quality Gates
- Pre-commit: syntax, format, static/type, security, architecture, AI behavior, tests+coverage, docs, complexity, performance, commit schema.
- CI PR checks mirror and publish reports.

## Maturity
- Current: **L2.5** (Single-Agent Sandbox).
- Path to L3: flip flags in `feature_flags.yml` when ready (docs auto-updates, standards sync PRs, limited auto-refactors).
