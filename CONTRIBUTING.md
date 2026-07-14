# Contributing to py-rizmi

## Development Setup

```bash
# Clone the repo
git clone https://github.com/Ramzi-Hadrouk/py-rizmi.git
cd py-rizmi

# Install with all extras (GUI + dev tools)
uv sync --extra all

# Or install core + dev only (no GUI)
uv sync --extra dev
```

## Project Layout

```
src/py_rizmi/
├── __init__.py          # Public API surface (__all__)
├── core/                # Cryptographic and fingerprint primitives
├── models/              # Data models (LicensePayload)
├── integrations/        # Server-side and third-party helpers
├── gui/                 # PyQt6 GUI (optional [gui] extra)
├── cli/                 # Typer CLI (rizmi command)
└── _internal/           # Private implementation details — do not import
```

## Running Tests

```bash
# Fast unit tests only
uv run pytest tests/unit -m "not slow"

# e2e tests (simulates missing [gui] extra)
uv run pytest tests/e2e -v

# Full suite (including GUI, integration, contract tests)
uv run pytest

# With coverage
uv run pytest --cov=py_rizmi --cov-report=term-missing
```

### Test Directory Layout

```
tests/
├── test_*.py          # Core unit tests (flat, legacy location)
├── unit/models/       # Model unit tests
├── gui/               # PyQt6 widget tests (require [gui] extra)
└── e2e/               # End-to-end integration tests
    └── test_no_extras_gui.py  # Guards the friendly-error path
```

## Code Style

- **Linting:** `uv run ruff check .`
- **Formatting:** `uv run ruff format .`
- **Type checking:** `uv run mypy src`

All three must pass before submitting a pull request.

## GUI Optional-Dependency Rule

**Critical:** `py_rizmi.gui` and any `PyQt6` symbol must **never** be imported
at the top level of `cli/app.py` or any module that is imported at CLI startup.
All GUI imports must be deferred to inside the function body of the command that
needs them. This is what keeps the `[gui]` extra genuinely optional.

Violating this will be caught by the `tests/e2e/test_no_extras_gui.py` suite.

## Deprecation Policy

When renaming or removing a public symbol (from `__all__`), use the deprecation-shim pattern:

```python
import warnings

def old_name(*args, **kwargs):
    """Deprecated: use ``new_name`` instead."""
    warnings.warn(
        "old_name is deprecated, use new_name instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return new_name(*args, **kwargs)
```

The deprecated symbol must remain functional for at least one MINOR release (or 6 months, whichever is longer) before removal.

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
