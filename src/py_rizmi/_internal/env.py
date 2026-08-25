"""Runtime environment detection for frozen builds.

Informational only: path resolution NEVER depends on this module
(see core.state_store for the path rules). Under PyInstaller,
``sys.frozen`` is set and ``sys._MEIPASS`` points at a temp extraction
dir. Under Nuitka, ``__compiled__`` exists on the ``__main__`` module.
"""
from __future__ import annotations

import sys

__all__ = ["is_frozen", "packager"]


def is_frozen() -> bool:
    """True under PyInstaller (sys.frozen) or Nuitka (__compiled__)."""
    if getattr(sys, "frozen", False):
        return True
    main = sys.modules.get("__main__", None)
    return main is not None and hasattr(main, "__compiled__")


def packager() -> str:
    """Best-effort packager name: 'nuitka' | 'pyinstaller' | 'none'."""
    main = sys.modules.get("__main__", None)
    if main is not None and hasattr(main, "__compiled__"):
        return "nuitka"
    if getattr(sys, "frozen", False):
        return "pyinstaller"
    return "none"
