"""
modules/core.py — main logic for DG_vibecoder

This module owns:
  - overseer-implement
  - overseer-dump
  - patch parsing & application
  - GitHub mirror sync
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# ============================================================
# PATHS & CONFIG
# ============================================================

# This file lives in DG_vibecoder/modules/core.py
# Root folder is its parent directory's parent.
ROOT = Path(__file__).resolve().parent.parent

OVERSEER_DIR = ROOT / "overseer"
OVERSEER_FILE = OVERSEER_DIR / "overseer.txt"

LOGS_DIR = ROOT / "logs"

# Credentials JSON on Windows side, mounted into WSL
CREDENTIALS_FILE = "/mnt/c/credentials/credentials.json"

# Top-level directories to exclude from manifest + sync
EXCLUDE_TOP_LEVEL_DIRS = {"logs", "__pycache__"}


# ============================================================
# UTILS
# ============================================================

def debug(msg: str) -> None:
    print(f"[DEBUG] {msg}")


def ensure_dirs() -> None:
    OVERSEER_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def load_credentials() -> dict:
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Credentials file not found: {CREDENTIALS_FILE}")
    with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def win_to_wsl(path: str) -> str:
    """
    Convert Windows C:\\ style path to /mnt/c/ if needed.
    """
    path = path.replace("\\", "/")
    if len(path) >= 3 and path[1:3] == ":/":
        drive = path[0].lower()
        rest = path[3:]
        return f"/mnt/{drive}/{rest}"
    return path


# ============================================================
# GIT MIRROR SYNC
# ============================================================

def get_repo_paths():
    """
    Read credentials.json and compute:
      - repo_root: deadlygraphics repo root on WSL
      - mirror_dir: ai/apps/DG_vibecoder under that repo
    """
    creds = load_credentials()
    repo_win = creds["deadlygraphics"]["paths"]["local_repo"]
    repo_wsl = win_to_wsl(repo_win)
    repo_root = Path(repo_wsl)
    mirror_dir = repo_root / "ai" / "apps" / "DG_vibecoder"
    return repo_root, mirror_dir


def run_git(cmd, cwd: Path) -> int:
    debug(f"RUN git in {cwd}: {' '.join(cmd)}")
    proc = subprocess.run(
        cmd, cwd=str(cwd), text=True, capture_output=True
    )
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    return proc.returncode


def sync_to_github(message: str = "Vibecoder auto-sync") -> None:
    """
    Mirror the local DG_vibecoder folder into the deadlygraphics
    repo at ai/apps/DG_vibecoder, then git add/commit/push.
    """
    print("[SYNC] Syncing vibecoder → GitHub mirror...")
    repo_root, mirror_dir = get_repo_paths()
    mirror_dir.mkdir(parents=True, exist_ok=True)

    # Copy from ROOT → mirror_dir
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)

        # Skip .git if present anywhere
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
    # If nothing to commit, this will just print a message.
    run_git(["git", "commit", "-m", message], cwd=repo_root)
    run_git(["git", "push", "origin", "main"], cwd=repo_root)

    print("[SYNC] Git push complete.")


# ============================================================
# MANIFEST GENERATION (DUMP)
# ============================================================

def generate_manifest() -> str:
    """
    Build the overseer manifest of the DG_vibecoder folder.

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

    for path in sorted(ROOT.rglob("*")):
        if path.is_dir():
            continue

        rel = path.relative_to(ROOT)

        # Skip logs and __pycache__
        if len(rel.parts) > 0 and rel.parts[0] in EXCLUDE_TOP_LEVEL_DIRS:
            continue

        # Optionally skip overseer file itself to avoid self-noise
        if path == OVERSEER_FILE:
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
    MARCO: write current manifest to overseer/overseer.txt
    and sync to GitHub.
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
    Parse PATCH blocks from overseer text.

    Supported patterns:

      === PATCH START: relative/path ===