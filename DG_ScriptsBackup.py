# Script Name: DG_ScriptsBackup.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Cross-platform manager. Windows pushes to GitHub. Linux pulls from GitHub with auto-repair.

import os
import sys
import shutil
import subprocess
import argparse
import json
import platform
import time
from pathlib import Path

# --- Configuration ---
IS_WINDOWS = os.name == 'nt'

if IS_WINDOWS:
    # Windows Paths
    CREDENTIALS_FILE = r"C:\credentials\credentials.json"
    DEFAULT_SCRIPT = r"H:\My Drive\AI\DG_videoscraper.py"
else:
    # WSL/Linux Paths
    CREDENTIALS_FILE = "/mnt/c/credentials/credentials.json"
    DEFAULT_SCRIPT = "DG_videoscraper.py"

def log(msg, level="INFO"):
    print(f"[{level}] {msg}")

def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        log(f"Missing Credentials: {CREDENTIALS_FILE}", "FAIL")
        sys.exit(1)
    try:
        with open(CREDENTIALS_FILE, 'r') as f: return json.load(f)
    except Exception as e:
        log(f"Config Error: {e}", "FAIL"); sys.exit(1)

def run_command(command, cwd=None):
    try:
        subprocess.run(command, cwd=cwd, shell=True, check=True)
    except subprocess.CalledProcessError:
        log(f"Command failed: {command}", "FAIL"); sys.exit(1)

def get_remote_url(creds):
    user = creds["github"]["user"]
    repo = creds["deadlygraphics"]["repo_name"]
    token = creds["github"].get("token", "").strip()
    if token and "god" not in token.lower() and "XXX" not in token:
        return f"https://{token}@github.com/{user}/{repo}.git"
    return f"https://github.com/{user}/{repo}.git"

# --- WINDOWS: PUSH TO GITHUB ---
def push_mode(args, creds):
    if not IS_WINDOWS:
        log("Push mode is for Windows only.", "FAIL"); sys.exit(1)

    log("STARTING PUSH: Windows -> GitHub...", "INFO")
    repo_path = Path(creds["deadlygraphics"]["paths"]["local_repo"])
    source_path = Path(args.file_path if args.file_path else DEFAULT_SCRIPT)
    target_name = args.target_name if args.target_name else source_path.name
    dest_path = repo_path / target_name

    if not source_path.exists():
        log(f"File not found: {source_path}", "FAIL"); sys.exit(1)

    # Git Operations
    url = get_remote_url(creds)
    if not repo_path.exists():
        run_command(f'git clone "{url}" "{repo_path}"')

    email = creds["github"]["email"]
    user = creds["github"]["user"]
    run_command(f'git config user.email "{email}"', cwd=repo_path)
    run_command(f'git config user.name "{user}"', cwd=repo_path)
    run_command(f'git remote set-url origin "{url}"', cwd=repo_path)

    shutil.copy2(source_path, dest_path)
    run_command(f'git add "{target_name}"', cwd=repo_path)
    
    status = subprocess.run('git status --porcelain', cwd=repo_path, capture_output=True, text=True, shell=True)
    if status.stdout.strip():
        run_command(f'git commit -m "Update {target_name}"', cwd=repo_path)
        run_command('git push origin main', cwd=repo_path)
        log("Push Successful!", "SUCCESS")
    else:
        log("No changes to push.", "WARN")

# --- LINUX: PULL FROM GITHUB ---
def pull_mode(args, creds):
    if IS_WINDOWS:
        log("Pull mode is for Linux/WSL only.", "FAIL"); sys.exit(1)

    log("STARTING PULL: GitHub -> WSL...", "INFO")
    
    script_name = args.file_path if args.file_path else DEFAULT_SCRIPT
    script_name = os.path.basename(script_name)
    
    # --- PATH LOGIC ---
    repo_name = creds["deadlygraphics"]["repo_name"]
    # The Workspace Root is where the .git folder lives
    workspace_root = os.path.expanduser(f"~/workspace/{repo_name}")
    
    # Destination logic
    if "DG_ScriptsBackup" in script_name:
        dest_folder = os.path.join(workspace_root, "ai", "scripts")
        is_app = False
    else:
        app_folder = os.path.splitext(script_name)[0]
        dest_folder = os.path.join(workspace_root, "ai", "apps", app_folder)
        is_app = True

    # 1. Update Repo (With Self-Healing)
    gh_user = creds["github"]["user"]
    repo_url = f"https://github.com/{gh_user}/{repo_name}.git"
    
    # HEALING LOGIC: If folder exists but is NOT a git repo, rename it to backup
    if os.path.exists(workspace_root) and not os.path.exists(os.path.join(workspace_root, ".git")):
        backup_name = f"{workspace_root}_backup_{int(time.time())}"
        log(f"Folder exists but is not a Git repo. Moving to {backup_name}...", "WARN")
        shutil.move(workspace_root, backup_name)

    # Now standard clone/pull logic
    if not os.path.exists(workspace_root):
        os.makedirs(workspace_root, exist_ok=True)
        run_command(f'git clone "{repo_url}" .', cwd=workspace_root)
    else:
        run_command('git pull', cwd=workspace_root)

    # 2. Copy file from Repo Root to Destination
    os.makedirs(dest_folder, exist_ok=True)
    src = os.path.join(workspace_root, script_name)
    dst = os.path.join(dest_folder, script_name)
    
    if os.path.exists(src):
        shutil.copy2(src, dst)
        run_command(f'chmod +x "{dst}"')
        log(f"Installed to: {dst}", "SUCCESS")
    else:
        log(f"Script {script_name} not found in repo root. Did you push it?", "FAIL")
        sys.exit(1)

    # 3. Setup Dependencies (ONLY for Apps)
    if is_app:
        log("Checking App Dependencies...", "INFO")
        venv_dir = os.path.join(dest_folder, "venv")
        
        # Venv creation
        if not os.path.exists(venv_dir):
            try:
                # We assume python3-venv is installed. If not, user sees error.
                run_command(f"{sys.executable} -m venv venv", cwd=dest_folder)
            except:
                log("Venv creation failed. Try running: sudo apt-get install python3-venv", "WARN")

        # Pip Install
        pip = os.path.join(venv_dir, "bin", "pip")
        if os.path.exists(pip):
            run_command(f'"{pip}" install --quiet --upgrade pip')
            # Standard dependencies
            run_command(f'"{pip}" install --quiet yt-dlp tqdm requests beautifulsoup4 selenium undetected-chromedriver selenium-wire')
    
    log("WSL Update Complete!", "SUCCESS")

def main():
    creds = load_credentials()
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["push", "pull"])
    parser.add_argument("file_path", nargs="?")
    parser.add_argument("--name", dest="target_name")
    args = parser.parse_args()

    if args.mode == "push": push_mode(args, creds)
    elif args.mode == "pull": pull_mode(args, creds)

if __name__ == "__main__":
    main()