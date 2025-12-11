#!/usr/bin/env python3
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================

CREDENTIALS_FILE = "/mnt/c/credentials/credentials.json"
INCLUDE_EXT = {".py", ".txt", ".md", ".toml", ".bat", ".sh"}
EXCLUDE_DIRS = {"logs", ".git", "__pycache__"}


# ============================================================
# UTILS: PATH / CREDS
# ============================================================

def win_to_wsl(path: str) -> str:
    """
    Convert Windows path (C:\\Users\\...) to WSL path (/mnt/c/Users/...).
    """
    drive, rest = path.split(":", 1)
    drive = drive.lower()
    rest = rest.replace("\\", "/")
    return f"/mnt/{drive}{rest}"


def load_credentials() -> dict:
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Credentials file NOT found: {CREDENTIALS_FILE}")
    with open(CREDENTIALS_FILE, "r") as f:
        return json.load(f)


# ============================================================
# GITHUB PUSH (DEBUG MODE)
# ============================================================

def create_test_file(repo_path: str) -> Path:
    file_path = Path(repo_path) / "hello_from_vibecoder.txt"
    file_path.write_text(
        "Hello from DG_vibecoder! This is a debug test.\n",
        encoding="utf-8"
    )
    print(f"[OK] Test file created: {file_path}")
    return file_path


def set_git_remote(repo_path: str, username: str, token: str, repo_name: str):
    os.chdir(repo_path)
    remote_url = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
    print(f"[DEBUG] Setting git remote to: {remote_url}")

    if not Path(".git").exists():
        raise RuntimeError(f"ERROR: Not a git repository: {repo_path}")

    result = subprocess.run(
        ["git", "remote", "set-url", "origin", remote_url],
        capture_output=True, text=True
    )
    print(result.stdout, result.stderr)
    if result.returncode != 0:
        raise RuntimeError("Failed to set git remote URL")

    print("[OK] Git remote updated.")


def git_push(repo_path: str, message: str):
    os.chdir(repo_path)

    print("[DEBUG] git add .")
    result = subprocess.run(["git", "add", "."], capture_output=True, text=True)
    print(result.stdout, result.stderr)

    print(f"[DEBUG] git commit -m \"{message}\"")
    result = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True, text=True
    )
    print(result.stdout, result.stderr)

    print("[DEBUG] git push origin main")
    result = subprocess.run(
        ["git", "push", "origin", "main"],
        capture_output=True, text=True
    )
    print(result.stdout, result.stderr)

    if result.returncode != 0:
        raise RuntimeError("Git push FAILED.")
    print("[OK] Git push successful.")


def run_debug_push():
    print("=================================================")
    print("=== DG_vibecoder — DEBUG PUSH MODE (v3.0) =======")
    print("=================================================")

    creds = load_credentials()
    username = creds["github"]["user"]
    token = creds["github"]["token"]
    repo_name = creds["deadlygraphics"]["repo_name"]
    win_repo_path = creds["deadlygraphics"]["paths"]["local_repo"]
    repo_path = win_to_wsl(win_repo_path)

    print(f"[DEBUG] Windows repo path: {win_repo_path}")
    print(f"[DEBUG] WSL repo path: {repo_path}")

    if not os.path.exists(repo_path):
        print(f"[FATAL] Repo path does NOT exist on WSL: {repo_path}")
        return

    print("[DEBUG] Repo path exists.")
    create_test_file(repo_path)
    set_git_remote(repo_path, username, token, repo_name)
    git_push(repo_path, "DG_vibecoder v3.0 debug push")

    print("=================================================")
    print("=== DEBUG PUSH MODE COMPLETE ====================")
    print("=================================================")


# ============================================================
# OVERSEER: DUMP (MARCO)
# ============================================================

def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"<< ERROR READING FILE {path}: {e} >>"


def build_overseer_dump(target_folder: Path) -> str:
    """
    Build a snapshot string of all code/text files in target_folder.
    """
    lines = []
    lines.append("=== OVERSEER SNAPSHOT ===")
    lines.append(f"generated={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"target_folder={target_folder}")
    lines.append("")

    lines.append("=== FILES ===")

    file_count = 0
    for root, dirs, files in os.walk(target_folder):
        # prune excluded dirs
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in INCLUDE_EXT:
                continue

            abs_path = Path(root) / fname
            rel_path = abs_path.relative_to(target_folder)

            content = read_file(abs_path)
            file_count += 1

            lines.append(f"=== FILE START: {rel_path} ===")
            lines.append("<CONTENT>")
            lines.append(content)
            lines.append("</CONTENT>")
            lines.append("=== FILE END ===")
            lines.append("")

    lines.append("=== SUMMARY ===")
    lines.append(f"total_files={file_count}")
    lines.append("")
    return "\n".join(lines)


def run_overseer_dump():
    """
    MARCO:
      - Create per-timestamp snapshot (overseer_adjust.txt + history copy).
      - Overwrite logs/overseer_response.txt with the latest snapshot
        plus instructions for the LLM to add PATCH blocks.
    """
    print("=================================================")
    print("=== DG_vibecoder — OVERSEER DUMP MODE (v3.0) ====")
    print("=================================================")

    root_folder = Path(__file__).resolve().parent
    print(f"[INFO] Snapshotting folder: {root_folder}")

    # Build snapshot text
    snapshot_text = build_overseer_dump(root_folder)

    # 1) Per-timestamp logs (history)
    logs_root = root_folder / "logs"
    logs_root.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = logs_root / timestamp
    history_dir = log_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    adjust_path = log_dir / "overseer_adjust.txt"
    history_adjust_path = history_dir / "overseer_adjust.txt"

    adjust_path.write_text(snapshot_text, encoding="utf-8")
    history_adjust_path.write_text(snapshot_text, encoding="utf-8")

    print(f"[SUCCESS] Overseer adjust dump created at: {adjust_path}")
    print(f"[INFO] History copy saved at: {history_adjust_path}")

    # 2) Persistent working document at logs/overseer_response.txt
    working_doc_path = logs_root / "overseer_response.txt"

    response_template = f"""{snapshot_text}
=== PATCHES (TO BE FILLED BY LLM) ===

# Instructions:
# - ChatGPT should ADD patch blocks in this file using the format:
#
# === PATCH START: relative/path/to/file.py ===
# FIND:
# old text
# REPLACE:
# new text
# === PATCH END ===
#
# or:
#
# === PATCH START: relative/path/to/file.py ===
# INSERT_AFTER:
# line to match
# INSERT_TEXT:
# new text here
# === PATCH END ===
#
# No changes are applied until you run:
#   python3 DG_vibecoder.py overseer-implement
#
# You (the human) can paste the entire content of this file to ChatGPT,
# then paste ChatGPT's updated content back into this same file.
"""

    working_doc_path.write_text(response_template, encoding="utf-8")
    print(f"[INFO] Working doc updated: {working_doc_path}")

    print("")
    print("Next steps:")
    print("  1) Open logs/overseer_response.txt and paste its content to ChatGPT.")
    print("  2) ChatGPT will insert PATCH blocks under the PATCHES section.")
    print("  3) Save the updated file, then run:")
    print("       python3 DG_vibecoder.py overseer-implement")
    print("=================================================")


# ============================================================
# OVERSEER: PATCH PARSING & APPLY (POLO)
# ============================================================

class Patch:
    def __init__(self, file_rel: str):
        self.file_rel = file_rel
        self.mode = None  # "replace" or "insert_after"
        self.find_text = ""
        self.replace_text = ""
        self.insert_after = ""
        self.insert_text = ""


def parse_patches(response_text: str):
    """
    Parse all PATCH START/END blocks from a large working document.
    Returns a list of Patch objects.
    """
    patches = []
    lines = response_text.splitlines()

    current = None
    state = None  # None, "FIND", "REPLACE", "INSERT_AFTER", "INSERT_TEXT"

    for raw in lines:
        line = raw.rstrip("\n")

        if line.startswith("=== PATCH START:"):
            # Extract raw filename
            file_rel_raw = line[len("=== PATCH START:"):].strip()

            # Remove trailing "===" or any '=' clutter
            if file_rel_raw.endswith("==="):
                file_rel_raw = file_rel_raw[:-3].rstrip()
            while file_rel_raw.endswith("="):
                file_rel_raw = file_rel_raw[:-1].rstrip()

            file_rel_raw = file_rel_raw.strip()

            current = Patch(file_rel_raw)
            patches.append(current)
            state = None
            continue

        if line.startswith("=== PATCH END"):
            current = None
            state = None
            continue

        if current is None:
            continue

        if line.strip() == "FIND:":
            current.mode = "replace"
            state = "FIND"
            current.find_text = ""
            continue

        if line.strip() == "REPLACE:":
            state = "REPLACE"
            current.replace_text = ""
            continue

        if line.strip() == "INSERT_AFTER:":
            current.mode = "insert_after"
            state = "INSERT_AFTER"
            current.insert_after = ""
            continue

        if line.strip() == "INSERT_TEXT:":
            state = "INSERT_TEXT"
            current.insert_text = ""
            continue

        # Accumulate text for the current state
        if state == "FIND":
            current.find_text += (line + "\n")
        elif state == "REPLACE":
            current.replace_text += (line + "\n")
        elif state == "INSERT_AFTER":
            current.insert_after += (line + "\n")
        elif state == "INSERT_TEXT":
            current.insert_text += (line + "\n")

    # Strip trailing newlines
    for p in patches:
        if p.find_text:
            p.find_text = p.find_text.rstrip("\n")
        if p.replace_text:
            p.replace_text = p.replace_text.rstrip("\n")
        if p.insert_after:
            p.insert_after = p.insert_after.rstrip("\n")
        if p.insert_text:
            p.insert_text = p.insert_text.rstrip("\n")

    return patches


def apply_patch_to_file(root_folder: Path, patch: Patch) -> str:
    """
    Apply a single patch to the appropriate file.
    Returns a human-readable summary line.
    """
    target_path = root_folder / patch.file_rel

    if not target_path.exists():
        return f"[WARN] File not found: {patch.file_rel}"

    original = target_path.read_text(encoding="utf-8")

    if patch.mode == "replace":
        if patch.find_text not in original:
            return f"[WARN] FIND text not found in {patch.file_rel}"
        new_content = original.replace(patch.find_text, patch.replace_text, 1)
        target_path.write_text(new_content, encoding="utf-8")
        return f"[OK] Replace applied to {patch.file_rel}"

    elif patch.mode == "insert_after":
        idx = original.find(patch.insert_after)
        if idx == -1:
            return f"[WARN] INSERT_AFTER text not found in {patch.file_rel}"

        insert_pos = idx + len(patch.insert_after)
        new_content = original[:insert_pos] + "\n" + patch.insert_text + original[insert_pos:]
        target_path.write_text(new_content, encoding="utf-8")
        return f"[OK] Insert-after applied to {patch.file_rel}"

    else:
        return f"[WARN] Unknown patch mode for {patch.file_rel}"


def run_overseer_implement():
    """
    POLO:
      - Read logs/overseer_response.txt
      - Parse all PATCH blocks
      - Apply patches to files
      - Write logs/last_patch_report.txt
    """
    print("=================================================")
    print("=== DG_vibecoder — OVERSEER IMPLEMENT (v3.0) ====")
    print("=================================================")

    root_folder = Path(__file__).resolve().parent
    logs_root = root_folder / "logs"
    working_doc_path = logs_root / "overseer_response.txt"

    if not working_doc_path.exists():
        print(f"[FATAL] Working doc not found: {working_doc_path}")
        return

    response_text = working_doc_path.read_text(encoding="utf-8")
    patches = parse_patches(response_text)

    if not patches:
        print("[WARN] No patches found in overseer_response.txt. Nothing to do.")
        return

    print(f"[INFO] Parsed {len(patches)} patch block(s). Applying...")

    report_lines = []
    report_lines.append(f"PATCH REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Working doc: {working_doc_path}")
    report_lines.append("")

    for p in patches:
        summary = apply_patch_to_file(root_folder, p)
        print(summary)
        report_lines.append(summary)

    report_text = "\n".join(report_lines)
    last_report_path = logs_root / "last_patch_report.txt"
    last_report_path.write_text(report_text, encoding="utf-8")

    print("")
    print(f"[INFO] Patch report written to: {last_report_path}")
    print("NOTE: Current implementation does NOT remove patch blocks from")
    print("      overseer_response.txt. You can manually clear or archive them")
    print("      once you're happy with the applied changes.")
    print("=================================================")


# ============================================================
# MAIN DISPATCHER
# ============================================================

def print_usage():
    print("DG_vibecoder v3.0 — modes:")
    print("")
    print("  python3 DG_vibecoder.py debug-push")
    print("      Run the original hello-file + git push test.")
    print("")
    print("  python3 DG_vibecoder.py overseer-dump")
    print("      MARCO: Overwrite logs/overseer_response.txt with a full snapshot")
    print("      of the DG_vibecoder folder plus instructions for the LLM.")
    print("")
    print("  python3 DG_vibecoder.py overseer-implement")
    print("      POLO: Read logs/overseer_response.txt, apply all PATCH blocks")
    print("      to the codebase, and write logs/last_patch_report.txt.")
    print("")


def main():
    if len(sys.argv) < 2:
        print_usage()
        return

    mode = sys.argv[1].lower()

    if mode == "debug-push":
        run_debug_push()
    elif mode == "overseer-dump":
        run_overseer_dump()
    elif mode == "overseer-implement":
        run_overseer_implement()
    else:
        print(f"[ERROR] Unknown mode: {mode}")
        print_usage()


if __name__ == "__main__":
    main()
