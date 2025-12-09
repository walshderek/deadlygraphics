#!/usr/bin/env python3
"""
DG_vibecoder.py — Stable reset

Core features:
  - overseer-implement: apply PATCH blocks from overseer/overseer.txt
  - overseer-dump: write a manifest of the DG_vibecoder folder into overseer/overseer.txt
  - sync_to_github: mirror the local DG_vibecoder folder into the deadlygraphics repo
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from pathlib import Path
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================

# Local vibecoder root (this script's directory)
LOCAL_ROOT = Path(__file__).resolve().parent

# Overseer path
OVERSEER_DIR = LOCAL_ROOT / "overseer"
OVERSEER_FILE = OVERSEER_DIR / "overseer.txt"

# Credentials file (Windows side, mounted into WSL)
CREDENTIALS_FILE = "/mnt/c/credentials/credentials.json"

# Do not sync these top-level dirs into GitHub
EXCLUDE_TOP_LEVEL_DIRS = {"logs", "__pycache__"}


# ============================================================
# UTILS
# ============================================================

def debug(msg: str) -> None:
    print(f"[DEBUG] {msg}")


def load_credentials() -> dict:
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Credentials file not found: {CREDENTIALS_FILE}")
    with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def win_to_wsl(path: str) -> str:
    """
    Convert Windows C:\\ style path to /mnt/c/ style if needed.
    """
    path = path.replace("\\", "/")
    if len(path) >= 3 and path[1:3] == ":/":
        drive = path[0].lower()
        rest = path[3:]
        return f"/mnt/{drive}/{rest}"
    return path


def ensure_dirs() -> None:
    OVERSEER_DIR.mkdir(parents=True, exist_ok=True)
    (LOCAL_ROOT / "logs").mkdir(parents=True, exist_ok=True)


# ============================================================
# GIT MIRROR SYNC
# ============================================================

def get_repo_paths():
    """
    Read credentials.json and determine:
      - repo_root: deadlygraphics repo root on WSL
      - mirror_dir: ai/apps/DG_vibecoder folder inside that repo
    """
    creds = load_credentials()
    repo_win = creds["deadlygraphics"]["paths"]["local_repo"]
    repo_wsl = win_to_wsl(repo_win)
    repo_root = Path(repo_wsl)
    mirror_dir = repo_root / "ai" / "apps" / "DG_vibecoder"
    return repo_root, mirror_dir


def run_git(cmd, cwd: Path) -> int:
    debug(f"RUN git in {cwd}: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    return proc.returncode


def sync_to_github(message: str = "Vibecoder auto-sync") -> None:
    """
    Copy LOCAL_ROOT into ai/apps/DG_vibecoder in the deadlygraphics repo,
    excluding logs and __pycache__, then git add/commit/push.
    """
    print("[SYNC] Syncing vibecoder → GitHub mirror...")

    repo_root, mirror_dir = get_repo_paths()
    mirror_dir.mkdir(parents=True, exist_ok=True)

    # Copy files from LOCAL_ROOT → mirror_dir
    for path in LOCAL_ROOT.rglob("*"):
        rel = path.relative_to(LOCAL_ROOT)

        # Skip .git if inside workspace
        if ".git" in rel.parts:
            continue

        # Skip excluded top-level dirs
        if len(rel.parts) > 0 and rel.parts[0] in EXCLUDE_TOP_LEVEL_DIRS:
            continue

        dest = mirror_dir / rel

        if path.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)

    # Git operations
    run_git(["git", "add", "."], cwd=repo_root)
    # Commit may fail if there's nothing to commit, that's fine.
    run_git(["git", "commit", "-m", message], cwd=repo_root)
    run_git(["git", "push", "origin", "main"], cwd=repo_root)

    print("[SYNC] Git push complete.")


# ============================================================
# OVERSEER MANIFEST (DUMP)
# ============================================================

def generate_manifest() -> str:
    """
    Generate a manifest of the DG_vibecoder folder.

    Format:

      === OVERSEER MANIFEST START ===

      === FILE START: relative/path ===
      <file content>
      === FILE END: relative/path ===

      ...

      === OVERSEER MANIFEST END ===
    """
    lines = []
    lines.append("=== OVERSEER MANIFEST START ===")

    for path in sorted(LOCAL_ROOT.rglob("*")):
        if path.is_dir():
            continue

        rel = path.relative_to(LOCAL_ROOT)

        # Skip logs and __pycache__
        if len(rel.parts) > 0 and rel.parts[0] in EXCLUDE_TOP_LEVEL_DIRS:
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            content = f"<UNREADABLE FILE: {e}>"

        lines.append("")
        lines.append(f"=== FILE START: {rel} ===")
        lines.append(content)
        lines.append(f"=== FILE END: {rel} ===")

    lines.append("=== OVERSEER MANIFEST END ===")
    return "\n".join(lines)


def run_overseer_dump() -> None:
    """
    Write the current manifest to overseer/overseer.txt and sync to GitHub.
    """
    print("=== MARCO: overseer-dump ===")
    ensure_dirs()

    manifest = generate_manifest()
    OVERSEER_FILE.write_text(manifest, encoding="utf-8")
    print(f"[OK] Manifest written to {OVERSEER_FILE}")

    sync_to_github("Vibecoder auto-sync (dump)")
    print("[OK] overseer-dump complete.")


# ============================================================
# PATCH PARSING
# ============================================================

def parse_patches(text: str):
    """
    Parse PATCH blocks from overseer.txt.

    Supported patterns:

      === PATCH START: relative/path/to/file ===
      NEW_FILE:
      <full content>
      === PATCH END ===

      === PATCH START: some/file.py ===
      FIND:
      <old text>
      REPLACE:
      <new text>
      === PATCH END ===

      === PATCH START: some/file.py ===
      INSERT_AFTER:
      <anchor text>
      INSERT_TEXT:
      <text to insert after anchor>
      === PATCH END ===
    """
    lines = text.splitlines()
    patches = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("=== PATCH START:"):
            filename = line.replace("=== PATCH START:", "").replace("===", "").strip()
            block = {"file": filename, "ops": []}
            i += 1

            current_op = None
            buffer = []

            def flush():
                nonlocal current_op, buffer
                if current_op is not None:
                    block["ops"].append((current_op, "\n".join(buffer)))
                current_op = None
                buffer = []

            while i < len(lines) and not lines[i].strip().startswith("=== PATCH END"):
                raw = lines[i]
                stripped = raw.strip()

                if stripped == "NEW_FILE:":
                    flush()
                    current_op = "NEW_FILE"

                elif stripped == "FIND:":
                    flush()
                    current_op = "FIND"

                elif stripped == "REPLACE:":
                    flush()
                    current_op = "REPLACE"

                elif stripped == "INSERT_AFTER:":
                    flush()
                    current_op = "INSERT_AFTER"

                elif stripped == "INSERT_TEXT:":
                    flush()
                    current_op = "INSERT_TEXT"

                else:
                    buffer.append(raw)

                i += 1

            flush()
            patches.append(block)

        i += 1

    return patches


# ============================================================
# APPLY PATCHES (IMPLEMENT)
# ============================================================

def apply_patch(block: dict) -> str:
    """
    Apply a single patch block to the local filesystem (LOCAL_ROOT).
    """
    rel_path = Path(block["file"])
    target = LOCAL_ROOT / rel_path
    ops = block["ops"]

    # NEW FILE
    for op, data in ops:
        if op == "NEW_FILE":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(data, encoding="utf-8")
            return f"[NEW FILE] {rel_path}"

    # Must exist for other ops
    if not target.exists():
        return f"[WARN] File not found: {rel_path}"

    try:
        text = target.read_text(encoding="utf-8")
    except Exception as e:
        return f"[ERROR] Failed to read {rel_path}: {e}"

    original = text
    last_find = None
    last_anchor = None

    for op, data in ops:
        if op == "FIND":
            last_find = data

        elif op == "REPLACE":
            if not last_find:
                return f"[ERROR] REPLACE without FIND in {rel_path}"
            if last_find not in text:
                return f"[WARN] FIND text not found in {rel_path}"
            text = text.replace(last_find, data)

        elif op == "INSERT_AFTER":
            last_anchor = data

        elif op == "INSERT_TEXT":
            if not last_anchor:
                return f"[ERROR] INSERT_TEXT without INSERT_AFTER in {rel_path}"
            if last_anchor not in text:
                return f"[WARN] INSERT_AFTER anchor not found in {rel_path}"
            text = text.replace(last_anchor, last_anchor + "\n" + data)

    if text != original:
        try:
            target.write_text(text, encoding="utf-8")
        except Exception as e:
            return f"[ERROR] Failed to write {rel_path}: {e}"
        return f"[OK] Patched: {rel_path}"
    else:
        return f"[NO CHANGE] {rel_path}"


def run_overseer_implement() -> None:
    """
    Read overseer/overseer.txt, apply any PATCH blocks found, then sync to GitHub.
    """
    print("=== POLO: overseer-implement ===")
    ensure_dirs()

    if not OVERSEER_FILE.exists():
        print(f"[FATAL] No overseer file found at {OVERSEER_FILE}")
        return

    text = OVERSEER_FILE.read_text(encoding="utf-8")
    patches = parse_patches(text)
    print(f"[INFO] Found {len(patches)} patch block(s).")

    for block in patches:
        result = apply_patch(block)
        print(result)

    sync_to_github("Vibecoder auto-sync (implement)")
    print("[OK] overseer-implement complete.")


# ============================================================
# MAIN
# ============================================================

def print_usage() -> None:
    print("DG_vibecoder — stable reset")
    print("")
    print("Usage:")
    print("  python3 DG_vibecoder.py overseer-implement")
    print("  python3 DG_vibecoder.py overseer-dump")
    print("")


def main() -> None:
    if len(sys.argv) < 2:
        print_usage()
        return

    mode = sys.argv[1].lower()

    if mode == "overseer-implement":
        run_overseer_implement()
    elif mode == "overseer-dump":
        run_overseer_dump()
    else:
        print(f"[ERROR] Unknown mode: {mode}")
        print_usage()


if __name__ == "__main__":
    main()
