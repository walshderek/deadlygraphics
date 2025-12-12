#!/usr/bin/env python3
import subprocess
import sys

def run(cmd):
    print(f"\n[RUN] {' '.join(cmd)}")
    subprocess.run(cmd, text=True, check=True)

if __name__ == "__main__":
    print("=== Vibecoder Update Script (v3.0 Wired) ===")
    # Point to the SMART engine in modules
    engine = "modules/DG_vibecoder_github_push.py"
    
    # Run POLO (Implement) then MARCO (Dump)
    run(["python3", engine, "overseer-implement"])
    run(["python3", engine, "overseer-dump"])
    print("\n=== UPDATE COMPLETE ===")
