#!/usr/bin/env python3
"""CLI: Print the machine HWID (Task 4.3)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.hwid import HardwareIdentifier


if __name__ == "__main__":
    print("Raw fingerprint:", HardwareIdentifier.get_raw_fingerprint())
    print("HWID (SHA-256):", HardwareIdentifier.get_machine_id())
