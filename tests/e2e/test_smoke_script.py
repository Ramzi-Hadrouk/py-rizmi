"""E2E: the licensing flow works as a real subprocess.

Runs ``scripts/smoke_main.py`` under a fresh interpreter and asserts
both scenarios: a clean run succeeds (exit 0, "SMOKE OK") and a
tampered DB is detected (exit 3). This exercises trial issuance,
activation state, interop between two manager instances, and tamper
detection end to end — without any packaging tooling.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_MAIN = REPO_ROOT / "scripts" / "smoke_main.py"


def test_smoke_script_clean_run() -> None:
    res = subprocess.run(
        [sys.executable, str(SMOKE_MAIN)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=REPO_ROOT,
    )
    assert res.returncode == 0, f"stdout={res.stdout}\nstderr={res.stderr}"
    assert "SMOKE OK" in res.stdout


def test_smoke_script_detects_tampering() -> None:
    env = {**os.environ, "SMOKE_TAMPER": "1"}
    res = subprocess.run(
        [sys.executable, str(SMOKE_MAIN)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=REPO_ROOT,
        env=env,
    )
    assert res.returncode == 3, (
        f"tamper detection failed: rc={res.returncode}\n"
        f"stdout={res.stdout}\nstderr={res.stderr}"
    )
    assert "tamper detected OK" in res.stdout
