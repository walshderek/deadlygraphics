#!/usr/bin/env python3
import os
import json
import subprocess
from pathlib import Path
import sys
from datetime import datetime
import shutil


# ============================================================
# CONSTANTS — NO QUESTIONS, NO INTERACTION, NO GUESSING
# ============================================================

CREDENTIALS_FILE = "/mnt/c/credentials/credentials.json"

# Local vibecoder folder — everything happens HERE
LOCAL_ROOT = Path(__file__).resolve().parent

# Folder containing the working overseer file
OVERSEER_DIR = LOCAL_ROOT / "overseer"
OVERSEER_FILE = OVERSEER_DIR / "overseer.txt"

# GitHub mirror root (NEVER asked again)
def load_credentials():
    with open(CREDENTIALS_FILE, "r") as f:
        return json.load(f)

CREDS = load_credentials()
GIT_REPO_ROOT = Path(
    CREDS["deadlygraphics"]["paths"]["local_repo"]
    .replace("\\", "/")
    .replace("C:/", "/mnt/c/")
)

# Vibecoder mirror inside repo
GIT_VIBECODER_DIR = GIT_REPO_ROOT / "ai/apps/DG_vibecoder"


# ============================================================
# UTILS
# ============================================================

def repo(cmd):
    """Run a subprocess command."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode == 0


def ensure_dirs():
    OVERSEER_DIR.mkdir(exist_ok=True)
    (LOCAL_ROOT / "logs").mkdir(exist_ok=True)


# ============================================================
# GIT SYNC (Local Vibecoder → GitHub Repo)
# ============================================================

EXCLUDE_DIRS = {"logs", "history", "outputs", "__pycache__"}
EXCLUDE_PATTERNS = ["Zone.Identifier"]


def should_exclude(path: Path):
    """Determine whether a file/folder should be excluded from GitHub sync."""
    parts = set(p.lower() for p in path.parts)
    if any(x in parts for x in EXCLUDE_DIRS):
        return True
    for p in EXCLUDE_PATTERNS:
        if p in str(path):
            return True
    return False


def sync_to_github():
    print("[SYNC] Syncing vibecoder → GitHub mirror...")

    # Create destination folder if missing
    GIT_VIBECODER_DIR.mkdir(parents=True, exist_ok=True)

    # Walk local vibecoder folder
    for item in LOCAL_ROOT.rglob("*"):
        rel = item.relative_to(LOCAL_ROOT)
        dest = GIT_VIBECODER_DIR / rel

        if should_exclude(rel):
            continue

        if item.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            continue

        # Copy file
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, dest)

    print("[SYNC] Files copied. Running git commit + push...")

    os.chdir(str(GIT_REPO_ROOT))

    repo(["git", "add", "."])
    repo(["git", "commit", "-m", "Vibecoder auto-sync"])
    repo(["git", "push", "origin", "main"])

    print("[SYNC] Git push complete.")


# ============================================================
# OVERSEER — MARCO (Dump everything into overseer.txt)
# ============================================================

def generate_overseer_manifest():
    lines = ["=== OVERSEER MANIFEST START ==="]

    for p in sorted(LOCAL_ROOT.rglob("*")):
        if p.is_dir():
            continue
        if should_exclude(p.relative_to(LOCAL_ROOT)):
            continue
        if p == OVERSEER_FILE:
            continue

        rel = p.relative_to(LOCAL_ROOT)
        try:
            text = p.read_text(encoding="utf-8")
        except:
            text = "<BINARY FILE>"

        lines.append(f"\n=== FILE START: {rel} ===")
        lines.append(text)
        lines.append(f"=== FILE END: {rel} ===")

    lines.append("=== OVERSEER MANIFEST END ===")
    return "\n".join(lines)


def run_overseer_dump():
    print("=================================================")
    print("=== VIBECODER v4.2 — OVERSEER DUMP =============")
    print("=================================================")

    ensure_dirs()

    manifest = generate_overseer_manifest()
    OVERSEER_FILE.write_text(manifest, encoding="utf-8")

    print(f"[OK] Wrote overseer manifest → {OVERSEER_FILE}")

    # Push overseer.txt to GitHub automatically
    sync_to_github()

    print("=================================================")
    print("[OK] MARCO COMPLETE — Upload overseer.txt to ChatGPT")
    print("=================================================")


# ============================================================
# PARSE PATCH BLOCKS
# ============================================================

def parse_patches(text):
    patches = []
    block = None

    for line in text.splitlines():
        if line.startswith("=== PATCH START:"):
            fname = line.split(":", 1)[1].strip().replace("===", "").strip()
            block = {"file": fname, "ops": []}
            continue

        if line.startswith("=== PATCH END"):
            if block:
                patches.append(block)
                block = None
            continue

        if block is None:
            continue

        # Patch commands
        if line.startswith("FIND:"):
            block["ops"].append(("FIND", line[len("FIND:"):].strip()))
        elif line.startswith("REPLACE:"):
            block["ops"].append(("REPLACE", line[len("REPLACE:"):].strip()))
        elif line.startswith("INSERT_AFTER:"):
            block["ops"].append(("INSERT_AFTER", line[len("INSERT_AFTER:"):].strip()))
        elif line.startswith("INSERT_TEXT:"):
            block["ops"].append(("INSERT_TEXT", line[len("INSERT_TEXT:"):].strip()))
        else:
            # multiline insert text
            if block["ops"] and block["ops"][-1][0] == "INSERT_TEXT":
                prev = block["ops"].pop()
                block["ops"].append((
                    "INSERT_TEXT",
                    prev[1] + "\n" + line
                ))

    return patches


# ============================================================
# APPLY PATCHES TO FILES
# ============================================================

def apply_patch_to_file(base: Path, patch):
    file = base / patch["file"]

    if not file.exists():
        return f"[WARN] File not found: {patch['file']}"

    text = file.read_text(encoding="utf-8")

    for op, arg in patch["ops"]:
        if op == "FIND":
            if arg not in text:
                return f"[WARN] FIND text not in file: {patch['file']}"
            findtext = arg

        if op == "REPLACE":
            text = text.replace(findtext, arg)

        if op == "INSERT_AFTER":
            if arg not in text:
                return f"[WARN] INSERT_AFTER target not found: {patch['file']}"
            text = text.replace(arg, arg + "\n" + patch["ops"][-1][1])

        if op == "INSERT_TEXT":
            pass  # handled above

    file.write_text(text, encoding="utf-8")
    return f"[OK] Patched: {patch['file']}"


# ============================================================
# OVERSEER — POLO (Apply patches from overseer.txt)
# ============================================================

def run_overseer_implement():
    print("=================================================")
    print("=== VIBECODER v4.2 — OVERSEER IMPLEMENT =========")
    print("=================================================")

    ensure_dirs()

    if not OVERSEER_FILE.exists():
        print(f"[FATAL] overseer.txt missing at {OVERSEER_FILE}")
        return

    text = OVERSEER_FILE.read_text(encoding="utf-8")
    patches = parse_patches(text)

    print(f"[INFO] Found {len(patches)} patch blocks")

    for p in patches:
        print(apply_patch_to_file(LOCAL_ROOT, p))

    # AUTO-SYNC → GITHUB
    sync_to_github()

    print("=================================================")
    print("[OK] IMPLEMENT COMPLETE")
    print("=================================================")


# ============================================================
# MAIN
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 DG_vibecoder.py <mode>")
        print("Modes: overseer-dump, overseer-implement")
        return

    mode = sys.argv[1].lower()

    if mode == "overseer-dump":
        run_overseer_dump()
    elif mode == "overseer-implement":
        run_overseer_implement()
    else:
        print(f"[ERROR] Unknown mode: {mode}")


if __name__ == "__main__":
    main()
