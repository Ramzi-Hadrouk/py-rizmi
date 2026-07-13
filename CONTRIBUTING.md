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

# Full suite (including GUI, integration, contract tests)
uv run pytest

# With coverage
uv run pytest --cov=py_rizmi --cov-report=term-missing
```

## Code Style

- **Linting:** `uv run ruff check .`
- **Formatting:** `uv run ruff format .`
- **Type checking:** `uv run mypy src`

All three must pass before submitting a pull request.

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
