#!/usr/bin/env python3
"""CLI: Print the machine HWID (Task 4.3)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.hwid import HardwareIdentifier


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Print the machine hardware ID")
    parser.parse_args()
    print("HWID (SHA-256):", HardwareIdentifier.get_machine_id())
