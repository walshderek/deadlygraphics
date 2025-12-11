#!/usr/bin/env python3
import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

CREDENTIALS_PATH = "/mnt/c/credentials/credentials.json"

ROOT = Path(__file__).resolve().parent
OVERSEER_DIR = ROOT / "overseer"
OVERSEER_FILE = OVERSEER_DIR / "overseer.txt"
MODULES_DIR = ROOT / "modules"

LOCAL_REPO = Path("/mnt/c/Users/seanf/Documents/GitHub/deadlygraphics")


# ============================================================
# UTILS
# ============================================================

def load_credentials():
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(f"Missing credentials.json at {CREDENTIALS_PATH}")
    with open(CREDENTIALS_PATH, "r") as f:
        return json.load(f)


def run(cmd, cwd=None):
    """Run a subprocess and echo output."""
    print(f"[DEBUG] RUN: {cmd}")
    result = subprocess.run(cmd, cwd=cwd, text=True)
    return result.returncode


# ============================================================
# GIT MIRROR SYNC
# ============================================================

def sync_to_github(message):
    print("[SYNC] Syncing local vibecoder → GitHub mirror...")

    # Copy files from WSL to Windows repo
    for item in ROOT.iterdir():
        if item.name in ["logs", "__pycache__", ".git"]:
            continue
        dest = LOCAL_REPO / "ai/apps/DG_vibecoder" / item.name

        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    # Git commands
    run(["git", "add", "."], cwd=LOCAL_REPO)
    run(["git", "commit", "-m", message], cwd=LOCAL_REPO)
    run(["git", "push", "origin", "main"], cwd=LOCAL_REPO)

    print("[SYNC] Git push complete.")


# ============================================================
# OVERSEER IMPLEMENT (POLO)
# ============================================================

def parse_patch_blocks(text):
    """
    Extract patch blocks from overseer.txt.
    """
    blocks = []
    current = None

    for line in text.splitlines():
        if line.startswith("=== PATCH START:"):
            filename = line.split(":")[1].strip().split("===")[0].strip()
            current = {"file": filename, "content": []}
        elif line.startswith("=== PATCH END"):
            if current:
                blocks.append(current)
                current = None
        elif current:
            current["content"].append(line)

    return blocks


def implement_patches():
    """
    Applies patches from overseer.txt
    """
    if not OVERSEER_FILE.exists():
        print("[ERROR] overseer.txt not found.")
        return

    txt = OVERSEER_FILE.read_text(encoding="utf-8")
    patches = parse_patch_blocks(txt)

    print(f"[INFO] Found {len(patches)} patch block(s).")

    for patch in patches:
        target_path = ROOT / patch["file"]

        print(f"[OK] Overwriting file: {target_path}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text("\n".join(patch["content"]), encoding="utf-8")

    sync_to_github("Vibecoder auto-sync (implement)")


# ============================================================
# OVERSEER DUMP (MARCO)
# ============================================================

def generate_manifest():
    """
    Write a clean overseer.txt manifest.
    """
    OVERSEER_DIR.mkdir(exist_ok=True)

    lines = []
    lines.append("=== OVERSEER MANIFEST START ===\n")

    for p in sorted(ROOT.rglob("*")):
        if p.is_dir():
            continue
        if "overseer/overseer.txt" in str(p):
            continue
        rel = p.relative_to(ROOT)
        try:
            text = p.read_text(encoding="utf-8")
        except:
            text = "<BINARY FILE>"
        lines.append(f"=== FILE START: {rel} ===")
        lines.append(text)
        lines.append(f"=== FILE END: {rel} ===\n")

    lines.append("=== OVERSEER MANIFEST END ===\n")

    OVERSEER_FILE.write_text("\n".join(lines), encoding="utf-8")

    sync_to_github("Vibecoder auto-sync (dump)")


# ============================================================
# MAIN DISPATCHER
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 DG_vibecoder.py overseer-implement")
        print("  python3 DG_vibecoder.py overseer-dump")
        return

    mode = sys.argv[1]

    if mode == "overseer-implement":
        implement_patches()

    elif mode == "overseer-dump":
        generate_manifest()

    else:
        print(f"[ERROR] Unknown mode: {mode}")


if __name__ == "__main__":
    main()
