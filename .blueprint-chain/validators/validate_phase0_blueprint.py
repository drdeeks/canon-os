#!/usr/bin/env python3
"""
Validator for Phase 0: Foundation
Auto-generated from blueprint deliverables.
Validation Gate: 
"""

import json
import os
import sys
import re
import glob
from pathlib import Path

def find_project_root(step_file):
    """Walk up from step file to find project root (contains .blueprint-chain)."""
    p = Path(step_file).resolve()
    for parent in p.parents:
        if (parent / '.blueprint-chain').exists():
            return parent
    return None

def check_deliverable(project_root, deliverable):
    """Check a single deliverable. Returns (ok, message)."""
    path = deliverable['path']
    full_path = project_root / path
    is_dir = deliverable['is_dir']
    is_glob = deliverable['is_glob']
    hint = deliverable['validation_hint']

    if is_glob:
        matches = list(project_root.glob(path))
        if not matches:
            return False, f"No files matching glob: {path}"
        return True, f"Found {len(matches)} matches for {path}: {[str(m.relative_to(project_root)) for m in matches]}"

    if is_dir:
        if not full_path.is_dir():
            return False, f"Directory not found: {path}"
        return True, f"Directory exists: {path}"

    # File checks
    if not full_path.exists():
        return False, f"File not found: {path}"

    # Content validation hints
    if hint:
        if 'valid JSON' in hint.lower() or 'json' in hint.lower():
            try:
                json.loads(full_path.read_text())
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON in {path}: {e}"
            return True, f"Valid JSON: {path}"
        elif 'CL-' in hint or 'changelog' in hint.lower():
            content = full_path.read_text()
            if not re.search(r'CL-\d+', content):
                return False, f"No CL- entries in {path}"
            return True, f"CHANGELOG has CL- entries: {path}"
        elif 'executable' in hint.lower():
            if not os.access(full_path, os.X_OK):
                return False, f"Not executable: {path}"
            return True, f"Executable: {path}"
        elif 'yaml' in hint.lower() or 'yml' in hint.lower():
            try:
                import yaml
                yaml.safe_load(full_path.read_text())
            except Exception as e:
                return False, f"Invalid YAML in {path}: {e}"
            return True, f"Valid YAML: {path}"

    return True, f"File exists: {path}"

def main():
    if len(sys.argv) < 2:
        print("Usage: validator.py <step-file-path>")
        sys.exit(1)

    step_file = sys.argv[1]
    project_root = find_project_root(step_file)
    if not project_root:
        print("ERROR: Could not find project root (.blueprint-chain)")
        sys.exit(1)

    deliverables = [
    ]

    all_ok = True
    messages = []

    for d in deliverables:
        ok, msg = check_deliverable(project_root, d)
        messages.append(msg)
        if not ok:
            all_ok = False

    # Print all messages
    for msg in messages:
        print(msg)

    if all_ok:
        print(f"OK: Phase 0 validation passed")
        sys.exit(0)
    else:
        print(f"FAIL: Phase 0 validation failed")
        sys.exit(1)

if __name__ == '__main__':
    main()