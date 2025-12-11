#!/usr/bin/env python3
"""
Unified Vibecoder update script.

This script performs the standard development cycle:

    1) POLO  – Apply patches from overseer.txt
    2) MARCO – Dump a new overseer manifest + auto-sync to GitHub

Usage:

    python3 update.py

"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(cmd):
    print(f"\n[RUN] {' '.join(cmd)}")
    p = subprocess.run(cmd, text=True)
    if p.returncode != 0:
        print(f"[ERROR] Command failed: {cmd}")
        sys.exit(1)

def main():
    print("=== Vibecoder Update Script ===")

    # 1) POLO
    run(["python3", "DG_vibecoder.py", "overseer-implement"])

    # 2) MARCO
    run(["python3", "DG_vibecoder.py", "overseer-dump"])

    print("\n=== UPDATE COMPLETE ===")

if __name__ == "__main__":
    main()
