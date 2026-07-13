# API Stability Policy

This document defines which parts of `py-rizmi` are covered by SemVer guarantees and which are not.

## SemVer-Covered (Stable)

The following symbols are exported via `py_rizmi.__all__` and are the project's public API:

- `LicenseValidator`
- `LicenseIssuer`
- `KeyPair` (re-export of `KeyPairManager`)
- `MachineFingerprint` (re-export of `HardwareIdentifier`)
- `LicensePayload`

Changes to these symbols follow strict SemVer:

- **MAJOR** — any breaking change to signatures, return types, or `.lic` format (`schema_version` bump)
- **MINOR** — backward-compatible additions (new optional parameters, new fields)
- **PATCH** — bug fixes that don't change observable behavior

Deprecations are announced with a `DeprecationWarning` (using `stacklevel=2`) at least one MINOR release before removal.

## Stable but Not Guaranteed

Subpackage internals (e.g. `py_rizmi.core.crypto`, `py_rizmi.integrations.validation`) are usable but may change between MINOR releases without deprecation notice. Importing from subpackages directly is supported but not recommended for downstream consumers.

## Never Covered

`py_rizmi._internal.*` is private implementation detail. It may change or be removed at any time without notice or deprecation period. Do not import from `_internal` in production code.
