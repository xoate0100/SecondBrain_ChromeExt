#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Behavior Validation
Validates:
1. Write permissions (files are within allowed paths)
2. TDD compliance (code files have corresponding test files)
Reference: AI_SANDBOX_RULES.md - TDD is MANDATORY and BLOCKING
"""
import sys
import re
import subprocess
import pathlib
from typing import List, Set, Tuple

# Set UTF-8 encoding for Windows compatibility
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import yaml
except ImportError:
    print("[ai-guard] Warning: PyYAML not installed. Install with: pip install PyYAML")
    sys.exit(0)


def load_feature_flags():
    """Load feature flags to check if TDD enforcement is enabled"""
    flags_path = pathlib.Path("0_phase0_bootstrap/feature_flags.yml")
    if not flags_path.exists():
        return {}
    return yaml.safe_load(open(flags_path))


def get_staged_files() -> List[str]:
    """Get list of staged files"""
    try:
        output = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            text=True
        )
        return [f.strip() for f in output.splitlines() if f.strip()]
    except subprocess.CalledProcessError:
        return []


def is_code_file(file_path: str) -> bool:
    """Check if file is a code file (not test, config, or doc)"""
    path = pathlib.Path(file_path)
    ext = path.suffix.lower()

    # Code file extensions
    code_extensions = {'.ts', '.tsx', '.js', '.jsx', '.py', '.java', '.go', '.rs', '.cpp', '.c'}

    # Exclude test files, config files, and docs
    if is_test_file(file_path):
        return False

    # Exclude config and doc files
    config_patterns = ['config', 'setup', 'jest', 'webpack', 'tsconfig', 'package.json', 'requirements.txt']
    if any(pattern in path.name.lower() for pattern in config_patterns):
        return False

    return ext in code_extensions


def is_test_file(file_path: str) -> bool:
    """Check if file is a test file"""
    path = pathlib.Path(file_path)
    name = path.name.lower()

    # Test file patterns (from AI_SANDBOX_RULES.md)
    test_patterns = [
        r'\.test\.(ts|tsx|js|jsx|py)$',
        r'\.spec\.(ts|tsx|js|jsx|py)$',
        r'^test_.*\.py$',
        r'.*_test\.py$',
    ]

    # Check if in test directory
    if 'test' in path.parts or 'tests' in path.parts:
        return True

    # Check filename patterns
    for pattern in test_patterns:
        if re.search(pattern, name):
            return True

    return False


def find_corresponding_test(code_file: str, test_files: List[str]) -> str:
    """Find corresponding test file for a code file"""
    code_path = pathlib.Path(code_file)
    code_name = code_path.stem
    code_dir = code_path.parent

    # Test file patterns to check
    test_patterns = [
        f"{code_name}.test.ts",
        f"{code_name}.test.tsx",
        f"{code_name}.spec.ts",
        f"{code_name}.spec.tsx",
        f"test_{code_name}.py",
        f"{code_name}_test.py",
    ]

    # Check in same directory
    for test_file in test_files:
        test_path = pathlib.Path(test_file)
        if test_path.name in test_patterns:
            # Check if in same directory or test subdirectory
            if test_path.parent == code_dir or 'test' in test_path.parts:
                return test_file

    # Check in test directory structure
    # e.g., src/foo.ts -> tests/foo.test.ts
    for test_file in test_files:
        test_path = pathlib.Path(test_file)
        if test_path.stem.replace('.test', '').replace('.spec', '').replace('test_', '').replace('_test', '') == code_name:
            return test_file

    return None


def validate_write_permissions(staged_files: List[str], allowed_paths: Set[str]) -> Tuple[bool, List[str]]:
    """Validate that staged files are within allowed paths"""
    violations = []

    for file_path in staged_files:
        path = pathlib.Path(file_path)

        # Allow root files
        if path.name in ("README.md", ".pre-commit-config.yaml", ".gitignore", ".gitattributes"):
            continue

        # Check if file is within allowed paths
        if not any(str(path).startswith(allowed_path.rstrip('/')) for allowed_path in allowed_paths):
            violations.append(file_path)

    return len(violations) == 0, violations


def validate_tdd_compliance(staged_files: List[str], enforce_tdd: bool) -> Tuple[bool, List[str]]:
    """
    Validate TDD compliance: code files must have corresponding test files
    Reference: AI_SANDBOX_RULES.md - "Every code change MUST include corresponding test files"
    """
    if not enforce_tdd:
        return True, []

    code_files = [f for f in staged_files if is_code_file(f)]
    test_files = [f for f in staged_files if is_test_file(f)]

    violations = []

    for code_file in code_files:
        # Skip if it's a type definition file (usually tested indirectly)
        if code_file.endswith('.d.ts'):
            continue

        # Check if corresponding test file exists
        test_file = find_corresponding_test(code_file, test_files)

        if not test_file:
            # Check if test file already exists in repo (not staged but exists)
            code_path = pathlib.Path(code_file)
            possible_test_paths = [
                code_path.parent / f"{code_path.stem}.test.ts",
                code_path.parent / f"{code_path.stem}.spec.ts",
                pathlib.Path("tests") / code_path.relative_to("src") if "src" in code_path.parts else None,
            ]

            test_exists = False
            for test_path in possible_test_paths:
                if test_path and test_path.exists():
                    test_exists = True
                    break

            if not test_exists:
                violations.append(code_file)

    return len(violations) == 0, violations


def main():
    """Main validation function"""
    flags = load_feature_flags()
    guardrails = flags.get("ai_guardrails", {})
    enforce_tdd = guardrails.get("enforce_tdd_cycle", True)

    allowed_paths = set(flags.get("permissions", {}).get("write_to", []))

    staged_files = get_staged_files()

    if not staged_files:
        print("[ai-guard] No staged files, skipping validation")
        sys.exit(0)

    # 1. Validate write permissions
    write_ok, write_violations = validate_write_permissions(staged_files, allowed_paths)

    if not write_ok:
        print("[ai-guard] ERROR: Write outside allowed paths:")
        for violation in write_violations:
            print(f"  - {violation}")
        print(f"\nAllowed paths: {', '.join(allowed_paths)}")
        sys.exit(1)

    # 2. Validate TDD compliance
    if enforce_tdd:
        tdd_ok, tdd_violations = validate_tdd_compliance(staged_files, enforce_tdd)

        if not tdd_ok:
            print("[ai-guard] ERROR: TDD violation: Code files without corresponding test files:")
            for violation in tdd_violations:
                print(f"  - {violation}")
            print("\nTDD is MANDATORY and BLOCKING (AI_SANDBOX_RULES.md)")
            print("Every code change MUST include corresponding test files in the same commit.")
            print("\nTest file patterns:")
            print("  - TypeScript: *.test.ts, *.spec.ts")
            print("  - Python: test_*.py, *_test.py")
            print("  - Or in tests/ directory")
            sys.exit(1)

    print("[ai-guard] OK")


if __name__ == "__main__":
    main()
