# Script Name: DG_ScriptsBackup.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Cross-platform manager. Windows pushes. Linux pulls interactively (Fixes Sudo password issue).

import os
import sys
import shutil
import subprocess
import argparse
import json
import platform
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

def run_command(command, cwd=None):
    # shell=True ensures commands run like you typed them in terminal
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

# --- LINUX: PULL FROM GITHUB (DIRECT EXECUTION) ---
def pull_mode(args, creds):
    if IS_WINDOWS:
        log("Pull mode is for Linux/WSL only.", "FAIL"); sys.exit(1)

    log("STARTING PULL: GitHub -> WSL...", "INFO")
    
    script_name = os.path.basename(args.file_path if args.file_path else DEFAULT_SCRIPT)
    
    repo_name = creds["deadlygraphics"]["repo_name"]
    workspace_root = os.path.expanduser(f"~/workspace/{repo_name}")
    
    if "DG_ScriptsBackup" in script_name:
        dest_folder = os.path.join(workspace_root, "ai", "scripts")
        is_app = False
    else:
        app_folder = os.path.splitext(script_name)[0]
        dest_folder = os.path.join(workspace_root, "ai", "apps", app_folder)
        is_app = True

    gh_user = creds["github"]["user"]
    repo_url = f"https://github.com/{gh_user}/{repo_name}.git"

    # 1. Update Repo
    log(f"Updating Repo at {workspace_root}...", "INFO")
    if not os.path.exists(workspace_root):
        os.makedirs(workspace_root, exist_ok=True)
        run_command(f'git clone "{repo_url}" .', cwd=workspace_root)
    else:
        if not os.path.exists(os.path.join(workspace_root, ".git")):
            # Backup broken folder and re-clone
            backup = f"{workspace_root}_BACKUP"
            shutil.move(workspace_root, backup)
            os.makedirs(workspace_root, exist_ok=True)
            run_command(f'git clone "{repo_url}" .', cwd=workspace_root)
        else:
            run_command('git pull', cwd=workspace_root)

    # 2. File Install
    os.makedirs(dest_folder, exist_ok=True)
    src = os.path.join(workspace_root, script_name)
    dst = os.path.join(dest_folder, script_name)
    
    if os.path.exists(src):
        # Simple copy
        shutil.copy2(src, dst)
        run_command(f'chmod +x "{dst}"')
        log(f"Installed {script_name}", "SUCCESS")
    else:
        log(f"Script {script_name} not found in repo root!", "FAIL")
        sys.exit(1)

    # 3. Configs (Scraper only)
    if "scraper" in script_name:
        checklist = os.path.join(dest_folder, "scrapervideo_checklist.txt")
        if not os.path.exists(checklist):
             with open(checklist, "w") as f: f.write("# URLs here\n")

    # 4. Dependencies (DIRECT SHELL EXECUTION)
    # This ensures sudo works interactively
    if is_app:
        log("Checking Dependencies...", "INFO")
        
        # Run sudo commands directly. They will prompt user in terminal.
        subprocess.run("sudo apt-get update", shell=True)
        subprocess.run("sudo apt-get install -y python3 python3-pip python3-venv unzip wget ffmpeg", shell=True)
        
        if not shutil.which("opera"):
             print("\n[INFO] Installing Opera (May ask for password)...")
             subprocess.run("wget -q -O - https://deb.opera.com/archive.key | sudo apt-key add -", shell=True)
             subprocess.run("sudo sh -c 'echo \"deb https://deb.opera.com/opera-stable/ stable non-free\" > /etc/apt/sources.list.d/opera-stable.list'", shell=True)
             subprocess.run("sudo apt-get update", shell=True)
             subprocess.run("sudo apt-get install -y opera-stable", shell=True)

        # Venv & Pip
        venv_dir = os.path.join(dest_folder, "venv")
        if not os.path.exists(venv_dir):
             run_command(f"{sys.executable} -m venv venv", cwd=dest_folder)
             
        pip = os.path.join(venv_dir, "bin", "pip")
        log("Updating Python Libs...", "INFO")
        run_command(f'"{pip}" install --quiet --upgrade pip')
        run_command(f'"{pip}" install --quiet setuptools "blinker<1.8.0" webdriver-manager yt-dlp tqdm requests beautifulsoup4 selenium selenium-wire undetected-chromedriver')

    log("Done!", "SUCCESS")

def install_mode(args, creds):
    push_mode(args, creds)
    print("-" * 40)
    pull_mode(args, creds)

def main():
    creds = load_credentials()
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["push", "pull", "install"])
    parser.add_argument("file_path", nargs="?")
    parser.add_argument("--name", dest="target_name")
    args = parser.parse_args()

    if args.mode == "push": push_mode(args, creds)
    elif args.mode == "pull": pull_mode(args, creds)
    elif args.mode == "install": install_mode(args, creds)

if __name__ == "__main__":
    main()