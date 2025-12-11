#!/usr/bin/env python3
"""
Unified Vibecoder update script (v3.0 Wired).
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
    print("=== Vibecoder Update Script (v3.0 Wired) ===")

    # Use the Smart Engine in modules/
    vibecoder_engine = "modules/DG_vibecoder_github_push.py"

    # 1) POLO (Implement changes from logs/overseer_response.txt)
    run(["python3", vibecoder_engine, "overseer-implement"])

    # 2) MARCO (Snapshot to logs/overseer_response.txt)
    run(["python3", vibecoder_engine, "overseer-dump"])

    print("\n=== UPDATE COMPLETE ===")

if __name__ == "__main__":
    main()