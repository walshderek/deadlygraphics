#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from pathlib import Path

# CONFIG
ROOT = Path(__file__).resolve().parent
OVERSEER_FILE = ROOT / "overseer" / "overseer.txt"
MODULES_DIR = ROOT / "modules"
LOCAL_REPO = Path("/mnt/c/Users/seanf/Documents/GitHub/deadlygraphics")

# UTILS
def run(cmd, cwd=None):
    print(f"[DEBUG] RUN: {cmd}")
    subprocess.run(cmd, cwd=cwd, text=True, check=False)

def sync_to_github(message):
    print("[SYNC] Syncing local vibecoder -> GitHub mirror...")
    # Copy files
    for item in ROOT.iterdir():
        if item.name in ["logs", "__pycache__", ".git", "apps_managed"]: continue
        dest = LOCAL_REPO / "ai/apps/DG_vibecoder" / item.name
        if item.is_dir():
            if dest.exists(): shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    
    # Push
    run(["git", "add", "."], cwd=LOCAL_REPO)
    run(["git", "commit", "-m", message], cwd=LOCAL_REPO)
    run(["git", "push", "origin", "main"], cwd=LOCAL_REPO)
    print("[SYNC] Git push complete.")

# LOGIC
def parse_patch_blocks(text):
    blocks = []
    current = None
    for line in text.splitlines():
        if line.startswith("=== PATCH START:"):
            filename = line.split(":")[1].strip().split("===")[0].strip()
            current = {"file": filename, "content": []}
        elif line.startswith("=== PATCH END"):
            if current: blocks.append(current); current = None
        elif current:
            current["content"].append(line)
    return blocks

def implement_patches():
    if not OVERSEER_FILE.exists(): return print("[ERROR] overseer.txt missing")
    txt = OVERSEER_FILE.read_text(encoding="utf-8")
    patches = parse_patch_blocks(txt)
    print(f"[INFO] Found {len(patches)} patches.")
    for patch in patches:
        target = ROOT / patch["file"]
        print(f"[OK] Overwriting: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(patch["content"]), encoding="utf-8")
    sync_to_github("Vibecoder auto-sync (implement)")

def generate_manifest():
    lines = ["=== OVERSEER MANIFEST START ===\n"]
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or "overseer.txt" in str(p) or "apps_managed" in str(p): continue
        rel = p.relative_to(ROOT)
        try: text = p.read_text(encoding="utf-8")
        except: text = "<BINARY FILE>"
        lines.append(f"=== FILE START: {rel} ===\n{text}\n=== FILE END: {rel} ===\n")
    lines.append("=== OVERSEER MANIFEST END ===\n")
    (ROOT / "overseer").mkdir(exist_ok=True)
    OVERSEER_FILE.write_text("\n".join(lines), encoding="utf-8")
    sync_to_github("Vibecoder auto-sync (dump)")

# MAIN
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: DG_vibecoder.py [overseer-implement | overseer-dump | install-suite]")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == "overseer-implement": implement_patches()
    elif mode == "overseer-dump": generate_manifest()
    elif mode == "install-suite":
        if len(sys.argv) < 3: 
            print("[ERROR] Usage: install-suite <name>")
            sys.exit(1)
        suite = sys.argv[2]
        script = MODULES_DIR / "DG_app_manager.py"
        print(f"[VIBECODER] Dispatching Suite: {suite}")
        subprocess.run([sys.executable, str(script), "--suite", suite])
    else:
        print(f"[ERROR] Unknown mode: {mode}")
