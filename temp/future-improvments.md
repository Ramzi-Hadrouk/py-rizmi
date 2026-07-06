# Future Improvements

## 🔴 Critical

- **Add `LICENSE` file** — README says MIT, file doesn't exist. Legal exposure if distributed.
- **Clean up stale `egg-info/` dirs** — Both `src/license_tool.egg-info/` and `src/py_rizmi.egg-info/` exist, confusing for tooling.
- **Make `backend/license_check.py` a true drop-in** — Currently imports from `src.core`; needs its own copy of validation logic or be installable as a standalone package.

## 🟡 Developer Experience

- **Add `pip install` support** — Add `console_scripts` entry points in `pyproject.toml` so commands are on `$PATH` after install (`py-rizmi-gui`, `gen-keypair`, `get-hwid`, `issue-license`).
- **Replace `sys.path.insert` hack in scripts** — Use proper entry points + `python -m scripts.gen_keypair` pattern.
- **Add `src/__main__.py`** — So `python -m src` launches the GUI.
- **Keyboard shortcuts** — Ctrl+G (generate), Ctrl+S (save), Ctrl+C (copy), Ctrl+L (load).
- **Remember window geometry** — Use `QSettings` to save/restore size and position.
- **Recent files** — Remember last opened `.pem` / `.lic` paths across sessions.
- **Fix silent `except Exception: pass` in logo loading** — Log or show a placeholder instead.
- **Hand cursor on buttons** — `setCursor(Qt.CursorShape.PointingHandCursor)` for `QPushButton`.

## 🟠 Use Case Coverage

- **Strengthen HWID** — Add fallback identifiers (disk serial, `/etc/machine-id`, or user-registered ID) for VMs/containers where MAC+hostname is unstable.
- **Implement online mode** — `mode=online` exists in the payload but is never enforced. Either build a validation ping endpoint or remove the field.
- **License revocation (CRL)** — Add a signed certificate revocation list that blocks specific `license_id`s.
- **Trial licenses** — Add `trial: true` + `trial_days` fields; validator warns but doesn't block during trial.
- **Concurrent usage enforcement** — `max_clients` is stored but never checked. Either document as metadata-only or build server-side seat tracking.
- **Audit trail** — Log each issuance to a JSON audit file (`keys/.audit.json`).
- **License extension** — Add `issuer.extend(token, extra_days)` to re-sign with extended expiry.
- **Persist form defaults** — Save key size, grace days, expiry days via `QSettings`.

## 🟢 Testing

- **GUI smoke tests** — Instantiate each view and verify widgets exist.
- **End-to-end test** — Full cycle: generate keypair → issue license → validate → decode.
- **HWID edge cases** — Test with MAC changes, container environments, non-Linux OS.
- **`backend/` module tests** — Test `validate_license` with valid/missing/tampered inputs.

## 🔵 Polish

- **Dark mode toggle** — qdarktheme supports it; add a sun/moon icon in the sidebar footer.
- **Logo compositing** — Currently baked onto `#f5f5f5`. If theme background changes it will mismatch. Composite at load time from transparent PNG.
- **Move `MARKDOWN_CSS` to `theme.py`** — Keep styling constants centralized.
- **Feature validation** — `DynamicListWidget` allows empty strings; trim and warn on submit.
- **Pre-commit hooks** — Add `.pre-commit-config.yaml` with ruff & trailing-whitespace.

## Priority Order

1. Add `LICENSE` file
2. Console script entry points + clean `egg-info/` dirs
3. Implement CRL / revocation
4. Strengthen HWID with fallback identifiers
5. GUI polish — keyboard shortcuts, dark mode, QSettings
6. E2E tests + GUI smoke tests
7. Backend drop-in self-containment
