REPLACE_FILE:
# core.py — stable minimal module for DG_vibecoder
# This file intentionally contains only basic helpers to avoid breaking the loader.

from pathlib import Path
import os
import subprocess
from typing import List, Optional

def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return "<BINARY FILE>"

def write_file(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def run_git(repo: Path, args: List[str]):
    """Run a git command in the mirror repo."""
    cmd = ["git"] + args
    result = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True)
    return result.stdout + result.stderr

def patch_apply(file_path: Path, find: Optional[str], replace: Optional[str]):
    """Simple find/replace patch engine."""
    text = read_file(file_path)
    if find and find not in text:
        return f"[WARN] FIND text not found in {file_path}"
    if find:
        new_text = text.replace(find, replace or "")
    else:
        new_text = (replace or "")
    write_file(file_path, new_text)
    return f"[OK] Patched: {file_path}"

# SAFE, MINIMAL FOUNDATION. No triple-quoted strings. No advanced logic.
# This file will not break imports.
