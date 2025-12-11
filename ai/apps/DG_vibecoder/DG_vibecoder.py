#!/usr/bin/env python3
"""
DG_vibecoder.py — minimal stable loader

This file is intentionally tiny and should almost never change.
All real logic lives in modules/core.py.
"""

import sys
from pathlib import Path

# Ensure local modules are importable
ROOT = Path(__file__).resolve().parent
MODULES_DIR = ROOT / "modules"
if str(MODULES_DIR) not in sys.path:
    sys.path.insert(0, str(MODULES_DIR))

import core  # type: ignore  # imported from modules/core.py


def main() -> None:
    """
    Delegate all behavior to core.dispatch(argv).
    """
    core.dispatch(sys.argv)


if __name__ == "__main__":
    main()