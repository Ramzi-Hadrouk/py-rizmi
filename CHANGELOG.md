# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.1.0] - 2026-08-25

### Added
- **Developer-Experience Layer**: `LicenseGate` — a one-object facade over StateStore + LicenseActivator + TrialManager (+ optional keypin & watchdog). `gate.start()` / `gate.check()` / `gate.activate_token()` / `gate.activate_file()` / `status_summary()` reduce typical integration to ~3 lines.
- **`LicenseStatus`**: rich, bool-friendly result type (`state`, `days_left`, `client`, `message`, `to_dict()`) shared across the gate, activator and CLI.
- **`rizmi doctor run`**: one-command health checklist — machine ID readable, clock sane, DB openable, row HMAC integrity, license/trial state, key-pin verification. `--json` and `--strict`; a pinned-fingerprint mismatch is always an error.
- **`rizmi app status / activate / deactivate`**: inspect and manage an installation's licensing from the terminal. `activate` validates against the vendor public key before storing; supports `--machine-id` for foreign DBs and `--token -` (stdin) to keep licenses out of shell history.
- **`rizmi init <App>`**: scaffolder that generates a keypair and prints a paste-ready `LicenseGate` snippet with the fingerprint pre-filled.
- **`rizmi migrate-to-sqlite run`**: idempotent CLI wrapper around `migrate_legacy_state()`.
- **Example recipes**: `examples/simple_cli_app.py`, `examples/tkinter_activation_dialog.py`, `examples/fastapi_dependency.py` (compile-checked in CI).
- **Documentation site**: static site under `docs/site/` deployed via GitHub Pages (`docs.yml` workflow) — features, quick start, full CLI reference, integration guide, packaging guidance, troubleshooting playbook, vision & roadmap.

### Fixed
- License precedence hardening: an active-but-tampered license row now reports `licensed_invalid` through `LicenseGate.check()` instead of silently falling back to an active trial (`StateStore.active_license_unverified()` distinguishes "no license" from "license present but tampered").

## [2.0.0] - 2026-08-25

### Added
- **SQLite State Store (v2 architecture)**: `StateStore` — a single per-app, namespaced, tamper-evident SQLite database (stdlib only). Every row is HMAC-verified against a machine+app-bound key before use; editing or transplanting SQL data is always **detected** and rejected.
- **In-App License Activation**: `LicenseActivator` with two developer-hosted entry methods — `activate_token()` (user pastes the license into your UI) and `activate_file()` (user picks their `license.lic`). Full validation chain runs *before* anything is stored; `current()` re-validates on every read.
- **Public-Key Pinning**: `pin_fingerprint()` / `key_fingerprint()` + new CLI `rizmi keys fingerprint` — the embedded vendor public key is verified against a SHA-256 fingerprint constant at startup, refusing to run if either constant is patched.
- **Frozen-Build Support**: `_internal.env` detects Nuitka/PyInstaller; all state paths resolve from platformdirs user-data (never `__file__`). E2E smoke test runs the whole flow inside a compiled Nuitka standalone binary.
- **Multi-App Namespacing**: mandatory per-app `app_name` keys the HMAC and selects the storage directory; the unsafe `"py-rizmi"` default is refused in production use. Optional `shared_clock_namespace=True` gives all of one vendor's apps a collective clock-rollback ratchet.

### Changed
- **BREAKING**: the license-swap / replacement-authorization feature is removed entirely (`core/swap_auth.py`, `models/swap_payload.py`, `rizmi license create-swap-request|sign-swap|verify-swap`, the GUI Swap view) — it duplicated revocation + reissue workflows and confused developers.
- **BREAKING**: `RizmiConfig.swap_valid_minutes` removed; added `use_sqlite`, `db_path`, `allow_default_namespace`, `shared_clock_namespace`.
- `TrialManager(use_sqlite=True)` stores trial keypairs, the trial license and clock marks in the StateStore — no loose files in the config dir. File-based mode remains fully supported (legacy).
- `migrate_legacy_state()` imports file-era trial state into the store (idempotent).

### Security
- ClockGuard high-water marks now live redundantly in the DB *plus* one obfuscated fallback file: deleting either alone cannot reset the anti-rollback ratchet. Rollback refusal logic unchanged and covered by tests.

## [1.6.0] - 2026-08-23

### Added
- **License-Free Trial Periods**: `TrialManager` / `TrialStatus` issue a self-signed, HWID-bound, ClockGuard-protected trial license so clients can evaluate for N days without a real `license.lic`. CLI `rizmi trial status` / `rizmi trial reset` (with `--json`).
- **License Revocation**: `RevocationList`, `create_revocation_list`, `sign_revocation_list`, `verify_revocation_list` for publishing signed revocation lists; `LicenseValidator(revocation_list=...)` rejects revoked license IDs. New **Revocation** GUI tab.
- **Runtime Enforcement**: `LicenseWatchdog` / `LicenseWatchdogError` periodically re-validate a license and fire `on_violation` / `on_grace` callbacks for long-running apps without a restart.
- **Centralized Config**: `RizmiConfig` — one validated source of truth for configuration.
- **CLI Enhancements**: `--json` output on license commands, `rizmi license issue-from-json`, and local swap-request generation (`rizmi license create-swap-request`).
- **Strict Payload Validation**: `LicensePayload` / `LicenseSwapPayload` now validate strictly; grace-period semantics documented.
- **Secure Key Writes**: Generated and private keys are written with restricted file permissions.

### Changed
- **Swap-Auth API Extended**: added `create_replacement_authorization_payload`, `sign_authorization_payload`, `verify_authorization` and the `ReplacementAuthorizationPayload` model alongside the existing swap-request API.
- Consistent dependencies and versioning across build scripts.

### Fixed
- `swap`: enforce expiry at sign time and verify signature before semantic checks.

---

## [1.5.0] - 2026-08-19

### Added
- **License Swap Protocol**: Core cryptographic protocol (`LicenseSwapPayload`, `canonicalize_payload`, `create_swap_request`, `sign_swap_request`, `verify_swap_authorization`) for authorizing license replacement without exposing private keys.
- **CLI Commands**: `rizmi license sign-swap` in `cli/commands/swap_cmd.py` to locally sign swap request files, and `rizmi license verify-swap` to verify signed license swap authorization `.rzswap` files.
- **PyQt6 GUI View**: Dedicated `License Swap` tab (`LicenseSwapTab` in `gui/views/swap_view.py`) allowing interactive selection of swap request JSON files and local signing with RSA private keys.
- **Contract & Security Unit Tests**: Integration contract tests simulating Django Phase 2 validation calls against dict and string JSON inputs, along with strict private key secrecy assertions.




---

## [1.4.5] - 2026-08-05

### Added
- Key Management Generate tab now displays small helper text explaining RSA key size options and that an optional passphrase protects the private key with AES encryption.

### Fixed
- Removed the "Use for License Generation" button from the Validate Keypair tab so validation remains focused on key matching only.
- Improved GUI test clarity and lint compliance for the KeyManager feature.

---

## [1.4.4] - 2026-07-27

### Added
- Optional passphrase encryption for private keys (`--passphrase` on `keys generate`,
  `--key-passphrase` / `RIZMI_KEY_PASSPHRASE` env var on `license issue`).
- Grace period enforcement: `grace_days` field is now enforced in `LicenseValidator`;
  expired licenses within the grace window return `in_grace_period=True` instead of
  raising immediately.
- `ERROR_MESSAGES` dictionary in `core/license_validator` centralizing all 7
  validation error reasons with human-readable text.
- Comprehensive GUI test suite (pytest-qt) covering all 5 views.
- Unit and contract tests for grace period behavior.

### Fixed
- Removed `pyqtdarktheme` from `[gui]` optional dependencies — the package never
  published v2.x to PyPI and has no Python 3.13 wheel, making `pip install py-rizmi[gui]`
  fail with `ResolutionImpossible` on Python 3.13.
- Replaced `qdarktheme.setup_theme()` with Qt's built-in Fusion style + `QPalette` +
  QSS — same light design, zero third-party theme libraries required.
- Pasted private keys in the GUI are now held in memory only (no temp file on disk).
- `guide_view.py` Integration Guide tab now finds `README.md` correctly in all layouts.
- Silent fallback on malformed numeric input in Generate License view now shows
  a validation error instead of silently substituting defaults.
- CLI and integration docstring now cover all 7 validation error reasons
  (previously missing `invalid_algorithm` and `unsupported_schema`).

---

## [1.2.0] - 2026-07-14

### Added
- Comprehensive test suite restructuring (Phase 6).
- Golden fixtures and contract tests to ensure forward/backward license compatibility.
- Hypothesis property tests for robust roundtrip issuance and signature mutation validation.
- Weekly cross-platform matrix testing workflow for CI.

### Fixed
- Fixed Issue #42: HWID validation is now case-insensitive, preventing false rejections from manually copied hardware IDs.

### Changed
- CI workflow split into `fast-tests` (unit tests + coverage) and `slow-tests` (GUI/integration using `pytest-xdist`).

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
