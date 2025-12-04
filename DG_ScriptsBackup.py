# Script Name: DG_ScriptsBackup.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Cross-platform manager to Push (Windows) and Pull/Install (Linux/WSL) scripts.

import os
import sys
import shutil
import subprocess
import argparse
import json
import platform
import time
from pathlib import Path

# --- Configuration & Paths ---
IS_WINDOWS = os.name == 'nt'

if IS_WINDOWS:
    # Windows Paths
    CREDENTIALS_FILE = r"C:\credentials\credentials.json"
    DEFAULT_SCRIPT = r"H:\My Drive\AI\DG_videoscraper.py"
    # We use H: for the bridge because we know it exists and is shared
    BRIDGE_DIR = r"H:\My Drive\AI" 
else:
    # WSL/Linux Paths
    CREDENTIALS_FILE = "/mnt/c/credentials/credentials.json"
    DEFAULT_SCRIPT = "DG_videoscraper.py"
    BRIDGE_DIR = "/mnt/h/My Drive/AI"

def log(msg, level="INFO"):
    print(f"[{level}] {msg}")

# --- Dependency Check ---
def check_dependencies():
    """Ensures minimal dependencies match."""
    # This script mainly needs standard library, but we check for requests just in case future needs
    try:
        import requests
    except ImportError:
        # We don't auto-install here to keep the manager lightweight, but we warn.
        pass

# --- Credentials ---
def load_config():
    if not os.path.exists(CREDENTIALS_FILE):
        log(f"Missing Credentials: {CREDENTIALS_FILE}", "FAIL")
        sys.exit(1)
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        log(f"Config Error: {e}", "FAIL"); sys.exit(1)

def get_remote_url(creds):
    user = creds["github"]["user"]
    repo = creds["deadlygraphics"]["repo_name"]
    token = creds["github"].get("token", "").strip()
    # Use Auth URL if token exists and isn't a placeholder
    if token and "god" not in token.lower() and "XXX" not in token:
        return f"https://{token}@github.com/{user}/{repo}.git"
    return f"https://github.com/{user}/{repo}.git"

# --- Utils ---
def run_command(cmd, cwd=None, shell=True):
    try:
        subprocess.run(cmd, cwd=cwd, shell=shell, check=True)
    except subprocess.CalledProcessError as e:
        log(f"Cmd Failed: {cmd}", "FAIL"); sys.exit(1)

# ==========================================
# WINDOWS LOGIC (PUSH & TRIGGER)
# ==========================================
def windows_push(args, creds):
    log("STARTING PUSH (Windows -> GitHub)", "INFO")
    
    # 1. Paths
    repo_path = Path(creds["deadlygraphics"]["paths"]["local_repo"])
    source_file = Path(args.file_path if args.file_path else DEFAULT_SCRIPT)
    target_name = args.target_name if args.target_name else source_file.name
    dest_file = repo_path / target_name

    if not source_file.exists():
        log(f"Source not found: {source_file}", "FAIL"); sys.exit(1)

    # 2. Git Setup
    url = get_remote_url(creds)
    if not repo_path.exists():
        log("Cloning Repo...", "WARN")
        run_command(f'git clone "{url}" "{repo_path}"')

    # 3. Identity
    email = creds["github"]["email"]
    user = creds["github"]["user"]
    run_command(f'git config user.email "{email}"', cwd=repo_path)
    run_command(f'git config user.name "{user}"', cwd=repo_path)
    run_command(f'git remote set-url origin "{url}"', cwd=repo_path)

    # 4. Copy & Push
    log(f"Copying {source_file.name}...", "INFO")
    shutil.copy2(source_file, dest_file)
    
    run_command(f'git add "{target_name}"', cwd=repo_path)
    
    # Check status
    res = subprocess.run('git status --porcelain', cwd=repo_path, capture_output=True, text=True, shell=True)
    if res.stdout.strip():
        run_command(f'git commit -m "Update {target_name}"', cwd=repo_path)
        run_command('git push origin main', cwd=repo_path)
        log("Push Complete!", "SUCCESS")
    else:
        log("No changes to push.", "WARN")

def windows_trigger_wsl_install(args, creds):
    log("STARTING REMOTE INSTALL (Windows -> WSL)", "INFO")
    
    wsl_user = creds["deadlygraphics"]["wsl_user"]
    wsl_pass = creds["deadlygraphics"].get("wsl_password", "")
    
    # Github URL (Public HTTPS for Linux pull)
    gh_user = creds["github"]["user"]
    repo = creds["deadlygraphics"]["repo_name"]
    public_url = f"https://github.com/{gh_user}/{repo}.git"

    # Directory Calculation
    # ~/workspace/deadlygraphics/ai/apps
    # We want to pull the WHOLE repo to ~/workspace/deadlygraphics
    wsl_repo_root = f"/home/{wsl_user}/workspace/{repo}"
    
    # --- GENERATE BASH SCRIPT ---
    # This script will run INSIDE WSL.
    bash_content = f"""#!/bin/bash
set -e
REPO_DIR="{wsl_repo_root}"
SUDO_PASS="{wsl_pass}"

echo "--> [WSL] Target: $REPO_DIR"

# 1. Setup Repo
if [ ! -d "$REPO_DIR" ]; then
    echo "--> [WSL] Cloning..."
    mkdir -p "$REPO_DIR"
    git clone "{public_url}" "$REPO_DIR"
else
    echo "--> [WSL] Pulling..."
    cd "$REPO_DIR"
    git pull
fi

# 2. Permissions
chmod +x $REPO_DIR/ai/apps/*.py 2>/dev/null || true

# 3. Dependencies
cd "$REPO_DIR"
if [ ! -d "venv" ]; then
    echo "--> [WSL] First Run Setup..."
    echo "$SUDO_PASS" | sudo -S apt-get update > /dev/null
    echo "$SUDO_PASS" | sudo -S apt-get install -y python3 python3-pip python3-venv unzip wget > /dev/null
    
    if ! command -v google-chrome &> /dev/null; then
        echo "--> [WSL] Installing Chrome..."
        wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | echo "$SUDO_PASS" | sudo -S apt-key add -
        echo "$SUDO_PASS" | sudo -S sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list'
        echo "$SUDO_PASS" | sudo -S apt-get update > /dev/null
        echo "$SUDO_PASS" | sudo -S apt-get install -y google-chrome-stable > /dev/null
    fi
    
    python3 -m venv venv
fi

source venv/bin/activate
echo "--> [WSL] Updating Pip Libs..."
pip install --quiet --upgrade pip
pip install --quiet yt-dlp tqdm requests beautifulsoup4 selenium undetected-chromedriver selenium-wire

echo "--> [WSL] SUCCESS! Apps updated."
"""

    # --- THE BRIDGE: WRITE TO FILE ---
    # We write this to H:\My Drive\AI\temp_dg_install.sh
    # WSL sees this as /mnt/h/My Drive/AI/temp_dg_install.sh
    
    bridge_filename = "temp_dg_install.sh"
    win_bridge_path = os.path.join(BRIDGE_DIR, bridge_filename)
    
    # We must construct the WSL path manually because we are on Windows
    # H:\My Drive\AI -> /mnt/h/My Drive/AI
    wsl_bridge_path = f"/mnt/h/My Drive/AI/{bridge_filename}"

    try:
        # Force UNIX line endings (\n) and UTF-8
        with open(win_bridge_path, "w", newline="\n", encoding="utf-8") as f:
            f.write(bash_content)
        
        log(f"Bridge script written to {win_bridge_path}", "INFO")
        
        # Execute via WSL
        # --cd ~ forces it to start in Linux Home, avoiding H: path translation errors
        cmd = f'wsl -u {wsl_user} --cd ~ bash "{wsl_bridge_path}"'
        subprocess.run(cmd, shell=True, check=True)
        
    except Exception as e:
        log(f"WSL Trigger Failed: {e}", "FAIL")
    finally:
        # Clean up the temp file
        if os.path.exists(win_bridge_path):
            os.remove(win_bridge_path)
            log("Cleaned up bridge script.", "INFO")

# ==========================================
# LINUX LOGIC (DIRECT PULL)
# ==========================================
def linux_pull(args, creds):
    # If run directly inside WSL, we can just do the git/pip stuff natively in Python
    # But honestly, re-using the bash logic above via subprocess is cleaner 
    # OR just simple python subprocess calls. Let's do simple python.
    
    log("STARTING PULL (Linux Native)", "INFO")
    
    wsl_user = creds["deadlygraphics"]["wsl_user"]
    repo_name = creds["deadlygraphics"]["repo_name"]
    gh_user = creds["github"]["user"]
    public_url = f"https://github.com/{gh_user}/{repo_name}.git"
    
    repo_dir = os.path.expanduser(f"~/workspace/{repo_name}")
    
    if not os.path.exists(repo_dir):
        os.makedirs(repo_dir, exist_ok=True)
        run_command(f'git clone "{public_url}" .', cwd=repo_dir)
    else:
        run_command('git pull', cwd=repo_dir)
        
    # Venv & Deps logic could go here, but usually the Windows trigger handles it.
    # We will assume if you run this manually on Linux, you just want the Code update.
    log("Code updated successfully.", "SUCCESS")


# --- Main Dispatcher ---
def main():
    check_dependencies()
    creds = load_config()

    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["push", "pull", "install"])
    parser.add_argument("file_path", nargs="?")
    parser.add_argument("--name", dest="target_name")
    args = parser.parse_args()

    if IS_WINDOWS:
        if args.mode == "push":
            windows_push(args, creds)
        elif args.mode == "install":
            # "Install" on Windows means: Push then Trigger Remote Install
            windows_push(args, creds)
            print("-" * 30)
            windows_trigger_wsl_install(args, creds)
        elif args.mode == "pull":
            log("Use 'install' on Windows to Push & Sync WSL.", "WARN")
            # But we can allow it just to trigger the WSL update without pushing
            windows_trigger_wsl_install(args, creds)
            
    else: # Linux/WSL
        if args.mode == "pull" or args.mode == "install":
            linux_pull(args, creds)
        else:
            log("Push mode not supported on Linux (Source is on H:)", "FAIL")

if __name__ == "__main__":
    main()