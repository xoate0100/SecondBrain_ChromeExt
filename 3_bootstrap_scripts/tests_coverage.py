#!/usr/bin/env python3
"""Run project tests and coverage once per pre-commit invocation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from pre_commit_utils import PIP_TIMEOUT, TEST_TIMEOUT, run_subprocess  # noqa: E402

try:
    import yaml
except ImportError:
    yaml = None


def load_thresholds() -> dict:
    defaults = {
        "backend_threshold": 100,
        "frontend_threshold": 95,
        "block_on_coverage": True,
    }
    flags_path = Path("0_phase0_bootstrap/feature_flags.yml")
    if not flags_path.exists() or yaml is None:
        return defaults
    try:
        with open(flags_path, "r", encoding="utf-8") as handle:
            flags = yaml.safe_load(handle) or {}
        components = flags.get("components", {})
        gates = flags.get("gates", {})
        return {
            "backend_threshold": components.get("backend", {}).get("coverage_threshold", 100),
            "frontend_threshold": components.get("frontend", {}).get("coverage_threshold", 95),
            "block_on_coverage": gates.get("block_on_coverage_drop", True),
        }
    except Exception:
        return defaults


def backend_has_python() -> bool:
    backend = Path("backend")
    if not backend.is_dir():
        return False
    return any(backend.rglob("*.py"))


def has_collectable_tests() -> bool:
    """True when pytest would collect at least one test module."""
    roots: list[Path] = []
    if Path("tests").is_dir():
        roots.append(Path("tests"))
    if backend_has_python():
        roots.append(Path("backend"))
    for root in roots:
        if any(root.rglob("test_*.py")) or any(root.rglob("*_test.py")):
            return True
    return False


def _restore_living_docs() -> None:
    """Tests may regenerate living docs; restore so pre-commit stays clean."""
    import subprocess

    for path in (
        "docs/PROJECT_STATUS.md",
        "6_ai_runtime_context/AI_CONTEXT.md",
        ".gitignore",
    ):
        if Path(path).exists():
            subprocess.run(["git", "checkout", "--", path], capture_output=True)


def _clear_exec_guard_log() -> None:
    log = Path("6_ai_runtime_context") / "EXEC_GUARD_LOG.jsonl"
    if log.is_file():
        try:
            log.unlink()
        except OSError:
            pass


def main() -> int:
    thresholds = load_thresholds()
    _clear_exec_guard_log()
    status = 0

    # README-only / placeholder backend (no .py, no tests): do not invoke
    # pytest — exit 5 (no tests collected) was bricking second-brain spokes.
    if backend_has_python() or has_collectable_tests():
        cov_backend = backend_has_python()
        coverage_file = Path("coverage-backend.dat").resolve()
        env = os.environ.copy()
        if cov_backend:
            env["COVERAGE_FILE"] = str(coverage_file)

        pip = run_subprocess(
            [sys.executable, "-m", "pip", "install", "--quiet", "pytest", "pytest-cov"],
            timeout=PIP_TIMEOUT,
        )
        if pip.returncode != 0:
            return pip.returncode

        pytest_cmd = [sys.executable, "-m", "pytest", "-q"]
        if cov_backend:
            pytest_cmd.extend(
                [
                    "--cov=backend",
                    "--cov-report=term-missing",
                    "--cov-report=json:coverage-backend.json",
                ]
            )
        pytest = run_subprocess(
            pytest_cmd,
            timeout=TEST_TIMEOUT,
            env=env,
        )
        _restore_living_docs()
        if pytest.returncode != 0:
            status = 1
        elif cov_backend:
            report = Path("coverage-backend.json")
            if report.exists():
                covered = json.loads(report.read_text(encoding="utf-8"))["totals"][
                    "percent_covered"
                ]
                if covered < thresholds["backend_threshold"] and thresholds["block_on_coverage"]:
                    print(
                        f"[coverage] Backend coverage {covered}% below threshold "
                        f"{thresholds['backend_threshold']}%"
                    )
                    status = 1
    elif Path("backend").is_dir():
        print("[tests-coverage] placeholder backend; no collectable tests — OK")

    if Path("frontend/package.json").is_file():
        npm_ci = run_subprocess(["npm", "ci", "--silent"], cwd="frontend", timeout=PIP_TIMEOUT)
        if npm_ci.returncode != 0:
            status = 1
        else:
            npm_test = run_subprocess(
                ["npm", "test", "--silent", "--", "--coverage"],
                cwd="frontend",
                timeout=TEST_TIMEOUT,
            )
            if npm_test.returncode != 0:
                status = 1
            else:
                print(
                    f"[coverage] Frontend tests passed (threshold: "
                    f"{thresholds['frontend_threshold']}%)"
                )

    _restore_living_docs()
    _clear_exec_guard_log()
    if status != 0:
        print("[tests-coverage] FAILED")
        return 1

    print("[tests-coverage] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
