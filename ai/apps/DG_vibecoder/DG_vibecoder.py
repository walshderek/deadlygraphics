#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parent
OVERSEER_FILE = ROOT / "overseer" / "overseer.txt"
GITHUB_ROOT = Path("/mnt/c/Users/seanf/Documents/GitHub/deadlygraphics")

# ============================================================
# UTILITIES
# ============================================================

def say(msg):
    print(msg, flush=True)

def run_git(args):
    """Run git inside the GitHub repo."""
    full_cmd = ["git"] + args
    say(f"[DEBUG] RUN git in {GITHUB_ROOT}: {' '.join(full_cmd)}")
    subprocess.run(full_cmd, cwd=GITHUB_ROOT)


def safe_read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except:
        return None


def safe_write(path, text):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


# ============================================================
# PATCH ENGINE
# ============================================================

def parse_patches(text):
    """
    Extract PATCH blocks of the form:

    === PATCH START: relative/path ===
    ...commands...
    === PATCH END ===
    """
    patches = []
    lines = text.splitlines()
    current = None

    for line in lines:
        if line.startswith("=== PATCH START:"):
            filename = line.replace("=== PATCH START:", "").replace("===", "").strip()
            current = {"file": filename, "content": []}
        elif line.startswith("=== PATCH END ==="):
            if current:
                patches.append(current)
            current = None
        elif current is not None:
            current["content"].append(line)

    return patches


def apply_patch_block(root, patch):
    file_rel = patch["file"]
    target_path = root / file_rel
    content = patch["content"]

    text = safe_read(target_path)
    if text is None:
        # Treat as "new file"
        new_content = "\n".join(content)
        safe_write(target_path, new_content)
        return f"[NEW FILE] {file_rel}"

    # Simple "replace whole file" model:
    new_content = "\n".join(content)
    safe_write(target_path, new_content)
    return f"[OK] Patched (full overwrite): {file_rel}"


# ============================================================
# GITHUB SYNC
# ============================================================

def sync_to_github(message):
    say("[SYNC] Syncing local vibecoder → GitHub mirror...")

    # Copy local folder into GitHub mirror
    for item in ROOT.rglob("*"):
        rel = item.relative_to(ROOT)
        dest = GITHUB_ROOT / "ai/apps/DG_vibecoder" / rel

        if item.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        else:
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(item.read_text(encoding="utf-8"), encoding="utf-8")
            except:
                pass  # Ignore binary files

    run_git(["add", "."])
    run_git(["commit", "-m", message])
    run_git(["push", "origin", "main"])

    say("[SYNC] Git push complete.")


# ============================================================
# MARCO (DUMP MANIFEST)
# ============================================================

def run_overseer_dump():
    say("=== MARCO: Generating overseer manifest ===")

    lines = []
    lines.append("=== OVERSEER MANIFEST START ===")

    for p in sorted(ROOT.rglob("*")):
        if p.is_dir():
            continue
        # do not include overseer.txt itself
        if p == OVERSEER_FILE:
            continue

        rel = p.relative_to(ROOT)

        txt = safe_read(p)
        if txt is None:
            txt = "<BINARY FILE>"

        lines.append(f"\n=== FILE START: {rel} ===")
        lines.append(txt)
        lines.append(f"=== FILE END: {rel} ===")

    lines.append("=== OVERSEER MANIFEST END ===")

    safe_write(OVERSEER_FILE, "\n".join(lines))
    sync_to_github("Vibecoder auto-sync (dump)")

    say("[OK] MARCO COMPLETE — overseer.txt updated")


# ============================================================
# POLO (APPLY PATCHES)
# ============================================================

def run_overseer_implement():
    say("=== POLO: Applying patches ===")

    text = safe_read(OVERSEER_FILE)
    if text is None:
        say(f"[FATAL] overseer.txt not found: {OVERSEER_FILE}")
        return

    patches = parse_patches(text)

    say(f"[INFO] Found {len(patches)} patch block(s).")

    for p in patches:
        summary = apply_patch_block(ROOT, p)
        say(summary)

    sync_to_github("Vibecoder auto-sync (implement)")

    say("[OK] POLO COMPLETE — patches applied")


# ============================================================
# DISPATCHER
# ============================================================

def print_usage():
    say("VIBECODER v5.0 — modes:")
    say("")
    say("  python3 DG_vibecoder.py overseer-implement")
    say("  python3 DG_vibecoder.py overseer-dump")
    say("")


def main():
    if len(sys.argv) < 2:
        print_usage()
        return
    
    mode = sys.argv[1].lower()

    if mode == "overseer-implement":
        run_overseer_implement()
    elif mode == "overseer-dump":
        run_overseer_dump()
    else:
        say(f"[ERROR] Unknown mode: {mode}")
        print_usage()


if __name__ == "__main__":
    main()
