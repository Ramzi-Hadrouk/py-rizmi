"""Examples compile and exist (no GUI/display required)."""
from __future__ import annotations

import compileall
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"

EXPECTED = (
    "simple_cli_app.py",
    "tkinter_activation_dialog.py",
    "fastapi_dependency.py",
)


def test_all_examples_compile() -> None:
    result = compileall.compile_dir(str(EXAMPLES), quiet=1, force=True)
    assert result, "example scripts must compile without syntax errors"


@pytest.mark.parametrize("name", EXPECTED)
def test_example_exists_and_mentions_rizmi(name: str) -> None:
    path = EXAMPLES / name
    assert path.exists()
    text = path.read_text()
    assert "py_rizmi" in text or "rizmi" in text
