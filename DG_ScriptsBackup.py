# Script Name: DG_ScriptsBackup.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Cross-platform manager. Windows pushes to GitHub. Linux pulls/installs with backups.

import os
import sys
import shutil
import subprocess
import argparse
import json
import platform
import datetime
from pathlib import Path

# --- Configuration ---
IS_WINDOWS = os.name == 'nt'

if IS_WINDOWS:
    CREDENTIALS_FILE = r"C:\credentials\credentials.json"
    DEFAULT_SCRIPT = r"H:\My Drive\AI\DG_videoscraper.py"
else:
    CREDENTIALS_FILE = "/mnt/c/credentials/credentials.json"
    DEFAULT_SCRIPT = "DG_videoscraper.py"

def log(msg, level="INFO"):
    print(f"[{level}] {msg}")

def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        log(f"Missing Credentials: {CREDENTIALS_FILE}", "FAIL"); sys.exit(1)
    try:
        with open(CREDENTIALS_FILE, 'r') as f: return json.load(f)
    except Exception as e:
        log(f"Config Error: {e}", "FAIL"); sys.exit(1)

def run_command(command, cwd=None, capture_output=False):
    """Runs command. Returns output if capture_output=True."""
    try:
        result = subprocess.run(
            command, 
            cwd=cwd, 
            shell=True, 
            check=True, 
            text=True, 
            stdout=subprocess.PIPE if capture_output else None
        )
        return result.stdout.strip() if capture_output else None
    except subprocess.CalledProcessError as e:
        if not capture_output:
            log(f"Command failed: {command}", "FAIL"); sys.exit(1)
        raise e

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

# --- LINUX: PULL WITH BACKUPS ---
def pull_mode(args, creds):
    if IS_WINDOWS:
        log("Pull mode is for Linux/WSL only.", "FAIL"); sys.exit(1)

    log("STARTING PULL: GitHub -> WSL...", "INFO")
    
    script_name = os.path.basename(args.file_path if args.file_path else DEFAULT_SCRIPT)
    
    # Paths
    wsl_user = creds["deadlygraphics"]["wsl_user"]
    repo_name = creds["deadlygraphics"]["repo_name"]
    workspace_root = os.path.expanduser(f"~/workspace/{repo_name}")
    
    # Destination logic
    if "DG_ScriptsBackup" in script_name:
        dest_folder = os.path.join(workspace_root, "ai", "scripts")
        is_app = False
    else:
        app_folder = os.path.splitext(script_name)[0]
        dest_folder = os.path.join(workspace_root, "ai", "apps", app_folder)
        is_app = True

    # 1. Update Repo (Smart Clone)
    gh_user = creds["github"]["user"]
    repo_url = f"https://github.com/{gh_user}/{repo_name}.git"
    
    if not os.path.exists(workspace_root):
        os.makedirs(workspace_root, exist_ok=True)
        run_command(f'git clone "{repo_url}" .', cwd=workspace_root)
    else:
        # If dir exists but is NOT a git repo (fix for your previous error)
        if not os.path.exists(os.path.join(workspace_root, ".git")):
             timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
             backup_path = f"{workspace_root}_BACKUP_{timestamp}"
             log(f"Existing folder is not a git repo. Moving to {backup_path}...", "WARN")
             shutil.move(workspace_root, backup_path)
             os.makedirs(workspace_root, exist_ok=True)
             run_command(f'git clone "{repo_url}" .', cwd=workspace_root)
        else:
             run_command('git pull', cwd=workspace_root)

    # Get Git Commit Info for Logging
    commit_hash = run_command("git rev-parse --short HEAD", cwd=workspace_root, capture_output=True)
    commit_msg = run_command("git log -1 --pretty=%B", cwd=workspace_root, capture_output=True)

    # 2. File Backup & Overwrite
    os.makedirs(dest_folder, exist_ok=True)
    src = os.path.join(workspace_root, script_name)
    dst = os.path.join(dest_folder, script_name)
    
    if os.path.exists(src):
        # BACKUP OLD FILE
        if os.path.exists(dst):
            backup_dir = os.path.join(dest_folder, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"{script_name}.{timestamp}.bak")
            shutil.copy2(dst, backup_file)
            log(f"Backed up previous version to: {backup_file}", "INFO")

        # OVERWRITE
        shutil.copy2(src, dst)
        run_command(f'chmod +x "{dst}"')
        
        # LOGGING
        log_file = os.path.join(dest_folder, "deployment.log")
        with open(log_file, "a") as f:
            log_entry = f"[{datetime.datetime.now()}] Updated {script_name} | Commit: {commit_hash} | Msg: {commit_msg.strip()}\n"
            f.write(log_entry)
        
        log(f"Installed to: {dst}", "SUCCESS")
    else:
        log(f"Script {script_name} not found in repo root.", "FAIL"); sys.exit(1)

    # 3. Dependencies (App Only)
    if is_app:
        log("Checking Dependencies...", "INFO")
        venv_dir = os.path.join(dest_folder, "venv")
        if not os.path.exists(venv_dir):
            try:
                run_command(f"{sys.executable} -m venv venv", cwd=dest_folder)
            except:
                log("Venv failed. Try: sudo apt install python3-venv", "WARN")

        pip = os.path.join(venv_dir, "bin", "pip")
        if os.path.exists(pip):
            run_command(f'"{pip}" install --quiet --upgrade pip')
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