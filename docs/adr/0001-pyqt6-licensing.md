# ADR 0001: PyQt6 Licensing Question

**Status:** Deferred  
**Date:** 2026-07-13  
**Owner:** Ramzi Hadrouk  
**Decision Deadline:** Before v1.0.0 release (Phase 10)

## Context

PyQt6 is licensed under GPLv3 for open-source use. If this project ever ships a
closed-source binary (e.g. via Nuitka compiled builds for paying customers), a
commercial PyQt6 license would be required. The current codebase is fully
open-source and MIT-licensed, so GPLv3 compliance via PyQt6 is satisfied today.

The risk is that a future closed-source distribution could be shipped without
resolving this question, inadvertently violating GPLv3.

## Decision

Defer the PyQt6 vs PySide6 decision. Revisit before any closed-source Nuitka
build ships to a paying customer, or before v1.0.0 if a closed-source build is
on the horizon.

## Consequences

- **If staying with PyQt6 for open-source only:** No action needed. GPLv3
 传染性 is satisfied by the project's own MIT license combined with PyQt6's
  terms.
- **If shipping closed-source binaries:** Must either purchase a commercial
  PyQt6 license from Riverbank Computing, or migrate to PySide6 (LGPL, more
  permissive for closed-source distribution).
- **Migration cost from PyQt6 to PySide6:** Moderate — API is nearly identical
  but import paths, signal/slot syntax, and some widget APIs differ. The
  migration should be straightforward if done before the GUI layer grows
  significantly.

## Notes

- PySide6 is the official Qt for Python binding, maintained by the Qt Company.
- PySide6 uses LGPL, which allows closed-source distribution without purchasing
  a commercial license.
- PyQt6 requires a commercial license for closed-source distribution.
- Both share ~95% API compatibility; differences are primarily in import paths
  and signal/slot declarations.
