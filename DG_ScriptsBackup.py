# Script Name: DG_ScriptsBackup.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Cross-platform manager. Windows pushes. Linux pulls, isolates apps, and creates global launchers.

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
    BRIDGE_DIR = r"H:\My Drive\AI" 
else:
    CREDENTIALS_FILE = "/mnt/c/credentials/credentials.json"
    DEFAULT_SCRIPT = "DG_videoscraper.py"
    BRIDGE_DIR = "/mnt/h/My Drive/AI"

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

# --- LINUX: PULL & INSTALL APP ---
def pull_mode(args, creds):
    if IS_WINDOWS:
        log("Pull mode is for Linux/WSL only.", "FAIL"); sys.exit(1)

    log("STARTING PULL: GitHub -> WSL...", "INFO")
    
    wsl_user = creds["deadlygraphics"]["wsl_user"]
    wsl_pass = creds["deadlygraphics"].get("wsl_password", "")
    
    script_name = os.path.basename(args.file_path if args.file_path else DEFAULT_SCRIPT)
    app_folder_name = os.path.splitext(script_name)[0]
    
    # Paths
    repo_name = creds["deadlygraphics"]["repo_name"]
    workspace_root = os.path.expanduser(f"~/workspace/{repo_name}")
    
    # Destination logic
    if "DG_ScriptsBackup" in script_name:
        dest_folder = os.path.join(workspace_root, "ai", "scripts")
        is_app = False
    else:
        dest_folder = os.path.join(workspace_root, "ai", "apps", app_folder_name)
        is_app = True

    gh_user = creds["github"]["user"]
    repo_url = f"https://github.com/{gh_user}/{repo_name}.git"

    # Bash Script: Handles Pulling, Isolating, Venv, and Shortcutting
    bash_content = f"""#!/bin/bash
set -e
REPO_DIR="{workspace_root}"
DEST_DIR="{dest_folder}"
SCRIPT_NAME="{script_name}"
APP_NAME="{app_folder_name}"
SUDO_PASS="{wsl_pass}"

echo "--> Target Repo: $REPO_DIR"

# 1. Update Master Repo
if [ ! -d "$REPO_DIR" ]; then
    echo "--> Cloning master repo..."
    mkdir -p "$REPO_DIR"
    git clone "{repo_url}" "$REPO_DIR"
else
    if [ ! -d "$REPO_DIR/.git" ]; then
        echo "--> Repairing non-git folder..."
        mv "$REPO_DIR" "$REPO_DIR_BACKUP_$(date +%s)"
        git clone "{repo_url}" "$REPO_DIR"
    else
        echo "--> Pulling latest code..."
        cd "$REPO_DIR"
        git pull
    fi
fi

# 2. App Isolation (Copy from Repo to App Folder)
mkdir -p "$DEST_DIR"
SRC="$REPO_DIR/$SCRIPT_NAME"
DST="$DEST_DIR/$SCRIPT_NAME"

if [ -f "$SRC" ]; then
    if [ -f "$DST" ]; then
        mkdir -p "$DEST_DIR/old"
        cp "$DST" "$DEST_DIR/old/$SCRIPT_NAME.$(date +%Y%m%d_%H%M%S).bak"
    fi
    cp "$SRC" "$DST"
    chmod +x "$DST"
    echo "--> Installed $SCRIPT_NAME to $DEST_DIR"
else
    echo "❌ Error: $SCRIPT_NAME not found in repo root!"
    exit 1
fi

# 3. Checklist & Configs
if [[ "$SCRIPT_NAME" == *"scraper"* ]]; then
    CHECKLIST="$DEST_DIR/scrapervideo_checklist.txt"
    if [ ! -f "$CHECKLIST" ]; then
        echo "# Paste URLs here (one per line)" > "$CHECKLIST"
        echo "--> Created checklist: $CHECKLIST"
    fi
fi

# 4. Dedicated VENV Setup (Apps Only)
if [[ "{str(is_app).lower()}" == "true" ]]; then
    cd "$DEST_DIR"
    
    # Ensure System Deps exist
    echo "$SUDO_PASS" | sudo -S apt-get update > /dev/null
    echo "$SUDO_PASS" | sudo -S apt-get install -y python3 python3-pip python3-venv unzip wget > /dev/null

    # Create isolated VENV for this app
    if [ ! -d "venv" ]; then
        echo "--> Creating dedicated venv for $APP_NAME..."
        python3 -m venv venv
    fi
    
    # Activate & Install specific requirements
    # Note: The script itself will handle specialized deps (like setuptools), 
    # but we ensure the basics are here.
    source venv/bin/activate
    echo "--> Pre-loading base dependencies..."
    pip install --quiet --upgrade pip
    pip install --quiet setuptools wheel
    
    # 5. Create Global Shortcut / Launcher
    # This creates a file in /usr/local/bin so you can type 'DG_videoscraper' anywhere
    LAUNCHER_PATH="/usr/local/bin/$APP_NAME"
    
    echo "--> Creating global launcher: $APP_NAME"
    
    # Write launcher script
    cat <<EOF > /tmp/$APP_NAME.launcher
#!/bin/bash
cd "$DEST_DIR"
source venv/bin/activate
python3 $SCRIPT_NAME "\$@"
EOF
    
    chmod +x /tmp/$APP_NAME.launcher
    echo "$SUDO_PASS" | sudo -S mv /tmp/$APP_NAME.launcher "$LAUNCHER_PATH"
    echo "$SUDO_PASS" | sudo -S chmod +x "$LAUNCHER_PATH"
    
    echo "✅ Shortcut created! You can now run '$APP_NAME' from anywhere."
fi
"""

    # Write to File Bridge
    temp_script_win = r"C:\dg_pull.sh"
    temp_script_wsl = "/mnt/c/dg_pull.sh"
    
    try:
        with open(temp_script_win, "w", newline="\n", encoding="utf-8") as f:
            f.write(bash_content)
        
        cmd = ["wsl", "-u", wsl_user, "--cd", "~", "bash", temp_script_wsl]
        subprocess.run(cmd, check=True)
        log("WSL Update & Install Successful", "SUCCESS")
        
    except Exception as e:
        log(f"WSL Install Failed: {e}", "FAIL")
    finally:
        if os.path.exists(temp_script_win):
            os.remove(temp_script_win)

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