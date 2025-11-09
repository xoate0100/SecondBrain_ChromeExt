#!/usr/bin/env python3
"""
Guardrail enforcement module.
Implements all guardrails defined in feature_flags.yml ai_guardrails section.
"""
import sys
import subprocess
import pathlib
from typing import List, Set

try:
    import yaml
except ImportError:
    print("[guardrail] Warning: PyYAML not installed. Install with: pip install PyYAML")
    sys.exit(0)


def load_feature_flags():
    """Load feature flags configuration"""
    flags_path = pathlib.Path("0_phase0_bootstrap/feature_flags.yml")
    if not flags_path.exists():
        print("[guardrail] Warning: feature_flags.yml not found")
        return {}
    return yaml.safe_load(open(flags_path))


def load_active_plan():
    """Load active plan for task scope validation"""
    plan_path = pathlib.Path("6_ai_runtime_context/ACTIVE_PLAN.yaml")
    if not plan_path.exists():
        return None
    try:
        return yaml.safe_load(open(plan_path))
    except:
        return None


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


def enforce_task_scope(guardrails: dict, staged_files: List[str]) -> bool:
    """
    Guardrail: enforce_task_scope
    Commits must modify only paths tied to current ACTIVE_TASK_POINTER.
    """
    if not guardrails.get("enforce_task_scope", False):
        return True  # Not enabled
    
    plan = load_active_plan()
    if not plan:
        print("[guardrail] enforce_task_scope: No active plan found, skipping")
        return True
    
    # Get current task from pointer
    pointer_path = pathlib.Path("6_ai_runtime_context/ACTIVE_TASK_POINTER.yaml")
    if pointer_path.exists():
        try:
            pointer = yaml.safe_load(open(pointer_path))
            current_task_id = pointer.get("current_task", 0)
        except:
            current_task_id = 0
    else:
        current_task_id = 0
    
    # Get expected outputs for current task
    tasks = plan.get("tasks", [])
    current_task = next((t for t in tasks if t.get("id") == current_task_id), None)
    
    if not current_task:
        print(f"[guardrail] enforce_task_scope: Task {current_task_id} not found, allowing")
        return True
    
    expected_outputs = current_task.get("outputs", [])
    if not expected_outputs:
        print(f"[guardrail] enforce_task_scope: Task {current_task_id} has no outputs, allowing")
        return True
    
    # Check if staged files match expected outputs
    violations = []
    for file_path in staged_files:
        path = pathlib.Path(file_path)
        # Check if file matches any expected output pattern
        matches = False
        for output in expected_outputs:
            if output.endswith("/"):
                # Directory pattern
                if str(path).startswith(output.rstrip("/")):
                    matches = True
                    break
            else:
                # File pattern
                if str(path) == output or str(path).startswith(output):
                    matches = True
                    break
        
        if not matches:
            violations.append(file_path)
    
    if violations:
        print("[guardrail] enforce_task_scope: Files outside task scope:")
        for v in violations:
            print(f"  - {v}")
        print(f"  Expected outputs: {expected_outputs}")
        return False
    
    return True


def forbid_folder_creation_outside_scope(guardrails: dict, staged_files: List[str]) -> bool:
    """
    Guardrail: forbid_folder_creation_outside_scope
    New directories validated against plan context; off-scope blocked.
    """
    if not guardrails.get("forbid_folder_creation_outside_scope", False):
        return True  # Not enabled
    
    flags = load_feature_flags()
    allowed_paths = set(flags.get("permissions", {}).get("write_to", []))
    
    violations = []
    for file_path in staged_files:
        path = pathlib.Path(file_path)
        
        # Check if file is in allowed write paths
        in_allowed = any(str(path).startswith(allowed) for allowed in allowed_paths)
        
        if not in_allowed:
            # Allow root files
            if path.name in ("README.md", ".pre-commit-config.yaml", ".gitignore"):
                continue
            violations.append(file_path)
    
    if violations:
        print("[guardrail] forbid_folder_creation_outside_scope: Files outside allowed paths:")
        for v in violations:
            print(f"  - {v}")
        print(f"  Allowed paths: {list(allowed_paths)}")
        return False
    
    return True


def enforce_tdd_cycle(guardrails: dict, staged_files: List[str]) -> bool:
    """
    Guardrail: enforce_tdd_cycle
    BLOCKING: Commits are blocked if code files are modified without corresponding test files.
    Enforces TDD discipline: Red → Green → Refactor → Document.
    """
    if not guardrails.get("enforce_tdd_cycle", False):
        return True  # Not enabled
    
    def is_test_file(file_path: str) -> bool:
        """Check if file is a test file based on patterns"""
        path_lower = file_path.lower()
        # Check for test directories
        if "/test" in path_lower or "/tests" in path_lower:
            return True
        # Python test patterns
        if file_path.endswith(("_test.py", "test_.py")):
            return True
        # TypeScript/JavaScript test patterns
        if file_path.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", ".test.js", ".spec.js")):
            return True
        return False
    
    def is_code_file(file_path: str) -> bool:
        """Check if file is a code file (not a test file)"""
        return file_path.endswith((".py", ".ts", ".tsx", ".js", ".jsx")) and not is_test_file(file_path)
    
    # Identify test files and code files
    test_files = [f for f in staged_files if is_test_file(f)]
    code_files = [f for f in staged_files if is_code_file(f)]
    
    # BLOCKING: If code files are modified without corresponding tests, block commit
    if code_files and not test_files:
        print("[guardrail] ❌ BLOCKING: TDD violation - Code modified without tests")
        print("[guardrail] Code files that need tests:")
        for cf in code_files:
            print(f"  - {cf}")
        print("[guardrail] TDD requires: Red → Green → Refactor → Document")
        print("[guardrail] Please add/update test files for all code changes before committing.")
        print("[guardrail] Test file patterns: *_test.py, test_*.py, *.test.ts, *.test.tsx, *.spec.ts, *.spec.tsx, files in test/ directories")
        return False  # Block commit
    
    return True


def require_doc_sync(guardrails: dict, staged_files: List[str]) -> bool:
    """
    Guardrail: require_doc_sync
    Checks that updated code sections have matching doc diffs.
    """
    if not guardrails.get("require_doc_sync", False):
        return True  # Not enabled
    
    # Check if code files modified
    code_files = [f for f in staged_files if f.endswith((".py", ".ts", ".tsx", ".js"))]
    doc_files = [f for f in staged_files if "docs" in f.lower() or f.endswith(".md")]
    
    if code_files:
        # Check if any doc files are also modified
        if not doc_files:
            print("[guardrail] require_doc_sync: Code modified without documentation updates")
            print("  Modified code:", code_files)
            print("  Tip: Update documentation when code changes")
            # Warning only, not blocking
            return True
    
    return True


def require_commit_plan_tags(guardrails: dict) -> bool:
    """
    Guardrail: require_commit_plan_tags
    Pre-commit hook ensures each commit message contains a plan/task tag.
    """
    if not guardrails.get("require_commit_plan_tags", False):
        return True  # Not enabled
    
    # Check commit message
    commit_msg_file = pathlib.Path(".git/COMMIT_EDITMSG")
    if commit_msg_file.exists():
        msg = commit_msg_file.read_text()
    else:
        # Try to get from git
        try:
            msg = subprocess.check_output(
                ["git", "log", "-1", "--pretty=%B"],
                text=True
            )
        except:
            return True  # Can't validate, allow
    
    # Check for plan/task tags
    if "plan:" not in msg.lower() and "task:" not in msg.lower():
        print("[guardrail] require_commit_plan_tags: Commit message missing plan/task tags")
        print("  Format: plan: <plan_id> | task: <task_id>")
        return False
    
    return True


def main():
    """Main guardrail enforcement"""
    flags = load_feature_flags()
    guardrails = flags.get("ai_guardrails", {})
    
    if not guardrails:
        print("[guardrail] No guardrails configured")
        sys.exit(0)
    
    staged_files = get_staged_files()
    
    results = []
    
    # Run all enabled guardrails
    results.append(("enforce_task_scope", enforce_task_scope(guardrails, staged_files)))
    results.append(("forbid_folder_creation_outside_scope", 
                   forbid_folder_creation_outside_scope(guardrails, staged_files)))
    results.append(("enforce_tdd_cycle", enforce_tdd_cycle(guardrails, staged_files)))
    results.append(("require_doc_sync", require_doc_sync(guardrails, staged_files)))
    results.append(("require_commit_plan_tags", require_commit_plan_tags(guardrails)))
    
    # Check results
    failed = [name for name, passed in results if not passed]
    
    if failed:
        print(f"[guardrail] Failed checks: {', '.join(failed)}")
        sys.exit(1)
    
    print("[guardrail] All checks passed")
    sys.exit(0)


if __name__ == "__main__":
    main()

