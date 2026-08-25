"""E2E: the SQLite licensing flow works inside a compiled Nuitka binary.

Builds ``scripts/frozen_smoke_main.py`` as a Nuitka standalone, runs it,
then corrupts a DB row and re-runs expecting detection (nonzero exit).
Skipped when Nuitka is not installed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_MAIN = REPO_ROOT / "scripts" / "frozen_smoke_main.py"

nuitka_available = shutil.which("nuitka") is not None


@pytest.mark.skipif(not nuitka_available, reason="nuitka not available")
def test_frozen_smoke(tmp_path: Path) -> None:
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    nuitka_cmd = shutil.which("nuitka")
    assert nuitka_cmd is not None
    subprocess.run(
        [
            nuitka_cmd,
            "--standalone",
            "--include-package=py_rizmi",
            "--output-dir", str(build_dir),
            str(SMOKE_MAIN),
        ],
        check=True,
        cwd=REPO_ROOT,
        timeout=1200,
    )
    binary_dir = build_dir / (SMOKE_MAIN.stem + ".dist")

    exe_candidates = list(binary_dir.glob(f"{SMOKE_MAIN.stem}*"))
    assert exe_candidates, f"no binary produced in {binary_dir}"
    binary = next(
        (c for c in exe_candidates if c.is_file() and os.access(c, os.X_OK)),
        exe_candidates[0],
    )

    # 1. clean run — full flow must succeed inside the frozen binary
    res = subprocess.run([str(binary)], capture_output=True, text=True, timeout=300)
    assert res.returncode == 0, f"stdout={res.stdout}\nstderr={res.stderr}"
    assert "frozen=True" in res.stdout
    assert "SMOKE OK" in res.stdout

    # 2. tampered run — detection must fire (exit 3)
    env = {**os.environ, "SMOKE_TAMPER": "1"}
    res2 = subprocess.run([str(binary)], capture_output=True, text=True, timeout=300, env=env)
    assert res2.returncode == 3, (
        f"tamper detection failed: rc={res2.returncode}\nstdout={res2.stdout}\nstderr={res2.stderr}"
    )


def test_smoke_script_passes_unfrozen_too() -> None:
    """Sanity: the same script passes under plain python."""
    res = subprocess.run(
        [sys.executable, str(SMOKE_MAIN)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=REPO_ROOT,
    )
    assert res.returncode == 0, f"stdout={res.stdout}\nstderr={res.stderr}"
    assert "SMOKE OK" in res.stdout
