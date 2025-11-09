#!/usr/bin/env python3
import sys, json, pathlib, time
# Minimal: ensure DOCUMENTATION_INDEX.md exists and references components
idx = pathlib.Path("4_docs_index/DOCUMENTATION_INDEX.md")
if not idx.exists():
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text("# Documentation Index\n\n- Meta: 0_phase0_bootstrap/\n- Standards: 1_global_standards/\n- Templates: 2_framework_templates/\n- Scripts: 3_bootstrap_scripts/\n- Components: frontend/ | backend/ | shared/\n- Plans: 6_ai_runtime_context/ACTIVE_PLAN.yaml\n- Architecture: 5_reference_architectures/LAYER_RULES.yaml\n", encoding="utf-8")
print("[docs] index present")

