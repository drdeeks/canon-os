#!/usr/bin/env python3
"""Read-only functional validation for the Phase 1 Core AI Engine gate."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_FILE = "tests/test_phase_1_core_ai_engine.py"


def main() -> int:
    if shutil.which("ffmpeg") is None:
        print("FAIL: FFmpeg is required for the Phase 1 MP4 assembly gate")
        return 1
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", TEST_FILE, "-v"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(completed.stdout, end="")
    print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode:
        print("FAIL: Phase 1 Core AI Engine functional gate failed")
        return completed.returncode
    print("OK: Phase 1 Core AI Engine gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
