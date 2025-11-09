#!/usr/bin/env python3
import sys, subprocess
cmd = sys.argv[1] if len(sys.argv)>1 else "help"

if cmd == "init":
    # Run initialization script
    subprocess.check_call(["python3", "3_bootstrap_scripts/init_project.py"])
elif cmd == "validate":
    subprocess.check_call(["pre-commit", "run", "--all-files"])
elif cmd == "trace":
    subprocess.check_call(["python3", "3_bootstrap_scripts/traceability_graph.py"])
elif cmd == "review":
    subprocess.check_call(["python3", "3_bootstrap_scripts/ai_review.py"])
elif cmd == "commit-checkpoint":
    # Run commit checkpoint script
    subprocess.check_call(["bash", "scripts/commit_checkpoint.sh"])
else:
    print("usage: python3 3_bootstrap_scripts/cli.py [init|validate|trace|review|commit-checkpoint]")
    print("\nCommands:")
    print("  init      - Initialize project from MVP_SPECIFICATION.yaml")
    print("  validate  - Run all pre-commit hooks")
    print("  trace     - Generate traceability graph")
    print("  review    - Run AI review")
    print("  commit-checkpoint - Commit with validation and proper message format")

