#!/usr/bin/env python3
# CLEAN RESET — Vibecoder v4.3 (stable)

import os
import sys
# ============================================================
# .vibeignore SUPPORT
# ============================================================

VIBEIGNORE_PATH = Path(__file__).resolve().parent / ".vibeignore"

def load_vibeignore():
    if VIBEIGNORE_PATH.exists():
        patterns = [x.strip() for x in VIBEIGNORE_PATH.read_text().splitlines() if x.strip()]
        return patterns
    return []

def should_ignore(path, ignore_patterns):
    p = str(path)
    for pat in ignore_patterns:
        if pat in p:
            return True
    return False

# ============================================================
# STATUS COMMAND
# ============================================================

def run_status(repo_path):
    print("=== VIBECODER STATUS ===")
    print(f"Repo path: {repo_path}")
    print(f"Overseer file: {LOCAL_OVERSEER_PATH}")

    if not LOCAL_OVERSEER_PATH.exists():
        print("[WARN] overseer.txt missing!")
    else:
        print("[OK] overseer.txt found")

    # Git status
    print("\n=== GIT STATUS ===")
    subprocess.run(["git", "status"], cwd=repo_path)

    print("\n=== LOCAL FILES ===")
    root = Path(__file__).resolve().parent
    for item in sorted(root.iterdir()):
        print(" -", item.name)

    print("\n=== IGNORE PATTERNS (.vibeignore) ===")
    ig = load_vibeignore()
    if ig:
        for p in ig:
            print("   •", p)
    else:
        print("   (none)")

# ============================================================
# DRY-RUN MODE
# ============================================================

def run_overseer_implement_dryrun():
    print("=== VIBECODER DRY-RUN ===")
    odoc = LOCAL_OVERSEER_PATH
    if not odoc.exists():
        print("[FATAL] overseer.txt missing.")
        return
    text = odoc.read_text()
    patches = parse_patches(text)
    if not patches:
        print("[INFO] No patches found.")
        return
    print(f"[INFO] Would apply {len(patches)} patches:")
    for p in patches:
        print(f" - {p['file']}")
    print("[DRY RUN COMPLETE — no files modified]")

import json
import subprocess
from pathlib import Path
from datetime import datetime
import shutil

# ============================================================
# CONFIG
# ============================================================

CREDENTIALS_FILE = "/mnt/c/credentials/credentials.json"

LOCAL_ROOT = Path(__file__).resolve().parent
OVERSEER_DIR = LOCAL_ROOT / "overseer"
OVERSEER_FILE = OVERSEER_DIR / "overseer.txt"

EXCLUDE_DIR_NAMES = {"logs", "history", "outputs", "__pycache__"}
EXCLUDE_SUBSTRINGS = {"Zone.Identifier"}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def debug(msg):
    print(f"[DEBUG] {msg}")

def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Credentials file not found: {CREDENTIALS_FILE}")
    with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def win_to_wsl(path: str):
    path = path.replace("\\", "/")
    if len(path) >= 3 and path[1:3] == ":/":
        drive = path[0].lower()
        rest = path[3:]
        return f"/mnt/{drive}/{rest}"
    return path

def ensure_dirs():
    OVERSEER_DIR.mkdir(exist_ok=True)
    (LOCAL_ROOT / "logs").mkdir(exist_ok=True)

def should_exclude(rel: Path):
    for part in rel.parts:
        if part in EXCLUDE_DIR_NAMES:
            return True
    for sub in EXCLUDE_SUBSTRINGS:
        if sub in str(rel):
            return True
    return False


# ============================================================
# GIT MIRROR SYNC
# ============================================================

def get_git_paths():
    creds = load_credentials()
    repo_win = creds["deadlygraphics"]["paths"]["local_repo"]
    repo_wsl = win_to_wsl(repo_win)
    repo_root = Path(repo_wsl)
    mirror_dir = repo_root / "ai" / "apps" / "DG_vibecoder"
    return repo_root, mirror_dir

def git(cmd, cwd):
    debug(f"RUNNING: {' '.join(cmd)}")
    p = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if p.stdout: print(p.stdout)
    if p.stderr: print(p.stderr)
    return p.returncode

def sync_to_github():
    print("[SYNC] Syncing vibecoder → GitHub mirror…")

    repo_root, mirror_dir = get_git_paths()
    mirror_dir.mkdir(parents=True, exist_ok=True)

    for path in LOCAL_ROOT.rglob("*"):
        rel = path.relative_to(LOCAL_ROOT)
        if should_exclude(rel):
            continue

        dest = mirror_dir / rel
        if path.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)

    git(["git", "add", "."], repo_root)
    git(["git", "commit", "-m", "Vibecoder auto-sync"], repo_root)
    git(["git", "push", "origin", "main"], repo_root)

    print("[SYNC] Git push complete.")


# ============================================================
# OVERSEER MANIFEST (MARCO)
# ============================================================

def generate_manifest():
    lines = ["=== OVERSEER MANIFEST START ==="]

    for path in sorted(LOCAL_ROOT.rglob("*")):
        if path.is_dir():
            continue

        rel = path.relative_to(LOCAL_ROOT)
        if should_exclude(rel):
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except:
            content = "<UNREADABLE FILE>"

        lines.append(f"\n=== FILE START: {rel} ===")
        lines.append(content)
        lines.append(f"=== FILE END: {rel} ===")

    lines.append("=== OVERSEER MANIFEST END ===")
    return "\n".join(lines)

def run_overseer_dump():
    print("=== MARCO: DUMPING MANIFEST ===")

    ensure_dirs()
    manifest = generate_manifest()
    OVERSEER_FILE.write_text(manifest, encoding="utf-8")

    sync_to_github()

    print("[OK] overseer.txt updated + pushed")


# ============================================================
# PATCH PARSER
# ============================================================

def parse_patch_blocks(text):
    lines = text.splitlines()
    patches = []
    i = 0

    while i < len(lines):
        if lines[i].startswith("=== PATCH START:"):
            filename = lines[i].split(":", 1)[1].replace("===", "").strip()
            block = {"file": filename, "ops": []}
            i += 1

            CURRENT = None
            buf = []

            def flush():
                nonlocal CURRENT, buf
                if CURRENT:
                    block["ops"].append((CURRENT, "\n".join(buf)))
                CURRENT = None
                buf = []

            while i < len(lines) and not lines[i].startswith("=== PATCH END"):
                line = lines[i].rstrip("\n")

                if line == "NEW_FILE:":
                    flush()
                    CURRENT = "NEW_FILE"

                elif line == "FIND:":
                    flush()
                    CURRENT = "FIND"

                elif line == "REPLACE:":
                    flush()
                    CURRENT = "REPLACE"

                elif line == "INSERT_AFTER:":
                    flush()
                    CURRENT = "INSERT_AFTER"

                elif line == "INSERT_TEXT:":
                    flush()
                    CURRENT = "INSERT_TEXT"

                else:
                    buf.append(line)

                i += 1

            flush()
            patches.append(block)

        i += 1

    return patches


# ============================================================
# APPLY PATCHES (POLO)
# ============================================================

def apply_patch(block):
    rel = Path(block["file"])
    target = LOCAL_ROOT / rel

    ops = block["ops"]

    # NEW FILE
    for op, data in ops:
        if op == "NEW_FILE":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(data, encoding="utf-8")
            return f"[NEW FILE] {rel}"

    # Must exist for other ops
    if not target.exists():
        return f"[WARN] File not found: {rel}"

    text = target.read_text(encoding="utf-8")
    original = text
    last_find = None
    last_anchor = None

    for op, data in ops:
        if op == "FIND":
            last_find = data

        elif op == "REPLACE":
            if last_find and last_find in text:
                text = text.replace(last_find, data)
            else:
                return f"[WARN] FIND text not found in {rel}"

        elif op == "INSERT_AFTER":
            last_anchor = data

        elif op == "INSERT_TEXT":
            if last_anchor and last_anchor in text:
                text = text.replace(last_anchor, last_anchor + "\n" + data)
            else:
                return f"[WARN] INSERT_AFTER anchor not found in {rel}"

    if text != original:
        target.write_text(text, encoding="utf-8")
        return f"[OK] Patched: {rel}"
    else:
        return f"[NO CHANGE] {rel}"


def run_overseer_implement():
    print("=== POLO: APPLYING PATCHES ===")

    ensure_dirs()

    if not OVERSEER_FILE.exists():
        print(f"[FATAL] No overseer.txt at {OVERSEER_FILE}")
        return

    text = OVERSEER_FILE.read_text(encoding="utf-8")
    patches = parse_patch_blocks(text)

    print(f"[INFO] Found {len(patches)} patch blocks.")

    for block in patches:
        print(apply_patch(block))

    sync_to_github()

    print("[OK] patches applied + pushed")


# ============================================================
# MAIN
# ============================================================

def usage():
    print("Usage:")
    print("  python3 DG_vibecoder.py overseer-dump")
    print("  python3 DG_vibecoder.py overseer-implement")

def main():
    if len(sys.argv) < 2:
        usage()
        return

    mode = sys.argv[1].lower()

    if mode == "overseer-dump":
        run_overseer_dump()
    elif mode == "overseer-implement":
        run_overseer_implement()
    else:
        usage()


if __name__ == "__main__":
    main()
