# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

---

## [1.1.0] - 2026-07-14

### Added
- `rizmi gui` CLI command — launches the PyQt6 desktop application directly
  from the `rizmi` CLI. All GUI imports are deferred inside the command
  function body so that a bare `pip install py-rizmi` (no `[gui]` extra)
  never triggers a Qt import at module load time.
- Friendly error message when `rizmi gui` is invoked without the `[gui]`
  extra installed. Exit code `1`, output includes `pip install py-rizmi[gui]`.
- `tests/e2e/test_no_extras_gui.py` — four tests that permanently guard the
  no-extras friendly-error path (Phase 5.2 regression suite).

### Changed
- `main.py` updated to use a deferred-import guard matching the CLI command,
  so `python main.py` also prints a clear install hint instead of a raw
  `ModuleNotFoundError` when PyQt6 is not installed.
- `cli/app.py` help table and `_print_help()` updated to include the `gui`
  command with a `(requires [gui] extra)` note.

---

## [1.0.1] - 2026-07-13


### Added
- Full `rizmi` CLI (Typer + Rich) with three command groups:
  - `rizmi keys generate` — generate RSA keypair with spinner and rich output
  - `rizmi keys inspect` — inspect any PEM file (type, size, fingerprint)
  - `rizmi keys verify` — verify a private/public key pair matches
  - `rizmi license issue` — sign and issue a `.lic` file with payload table
  - `rizmi license validate` — validate `.lic` against public key + HWID
  - `rizmi license inspect` — decode `.lic` without HWID or expiry check
  - `rizmi machine-id` — get HWID with `--raw` (pipe-friendly) and `--copy` flags
- `rizmi --version` / `-V` flag with banner output.
- Auto-creation of GitHub Release in the `release.yml` CI workflow.

### Removed
- `scripts/` directory (all three legacy scripts) — fully superseded by the `rizmi` CLI.

---

## [1.0.0] - 2026-07-13

### Added
- `src/py_rizmi/` src-layout with clean public API (`__all__` re-exports).
- `pyproject.toml` with Hatchling + hatch-vcs build backend.
- `[gui]` optional extra for PyQt6 dependencies.
- `[dev]` extra with pytest, ruff, mypy, hypothesis, and testing plugins.
- `[all]` extra installing both GUI and dev dependencies.
- `rizmi` console-script entry point (Typer CLI, Phase 4).
- `FingerprintProvider` Protocol for pluggable fingerprint backends.
- API stability policy (`docs/api-stability.md`).
- `CONTRIBUTING.md` with development setup and deprecation-shim pattern.

### Changed
- Migrated from flat `src/` layout to `src/py_rizmi/` src-layout.
- Moved RSA/signing primitives into `core/crypto.py`.
- Renamed `backend/` to `integrations/`.
- `LicensePayload` dataclass now includes `schema_version` field.
- GUI dependencies moved from core to optional `[gui]` extra.

### Deprecated
- Nothing yet (first release).

### Removed
- Old `src/core/`, `src/gui/`, `src/utils/`, `backend/`, `config/` directories.
- `nuitka` from core runtime dependencies (now dev-only).
