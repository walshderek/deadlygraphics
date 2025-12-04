# Script Name: DG_ScriptsBackup.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Cross-platform manager. Supports Single Files AND Project Folders.

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
    
    if not source_path.exists():
        log(f"Path not found: {source_path}", "FAIL"); sys.exit(1)

    # Determine Target Name
    target_name = args.target_name if args.target_name else source_path.name
    dest_path = repo_path / target_name

    log(f"Source: {source_path}", "INFO")
    log(f"Type: {'FOLDER' if source_path.is_dir() else 'FILE'}", "INFO")

    # 1. Git Init/Clone
    url = get_remote_url(creds)
    if not repo_path.exists():
        run_command(f'git clone "{url}" "{repo_path}"')

    # 2. Git Config
    email = creds["github"]["email"]
    user = creds["github"]["user"]
    run_command(f'git config user.email "{email}"', cwd=repo_path)
    run_command(f'git config user.name "{user}"', cwd=repo_path)
    run_command(f'git remote set-url origin "{url}"', cwd=repo_path)

    # 3. Copy Logic (File vs Folder)
    if source_path.is_dir():
        # Recursive Copy (Overwriting destination)
        if dest_path.exists():
            shutil.rmtree(dest_path)
        # ignore venv and pycache and .git
        shutil.copytree(source_path, dest_path, ignore=shutil.ignore_patterns('venv', '__pycache__', '.git', '*.pyc'))
    else:
        # Single File Copy
        shutil.copy2(source_path, dest_path)

    # 4. Push
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
    
    wsl_user = creds["deadlygraphics"]["wsl_user"]
    
    # Input can be a filename "DG_videoscraper.py" OR a folder name "DG_collect_Dataset"
    input_name = os.path.basename(args.file_path if args.file_path else DEFAULT_SCRIPT)
    
    # Logic to determine App Name and Entry Script
    if input_name.endswith(".py"):
        # It's a single file script
        app_name = os.path.splitext(input_name)[0]
        script_file = input_name
        is_folder = False
    else:
        # It's a folder project (e.g. DG_collect_Dataset)
        app_name = input_name
        # We assume the entry script matches the folder name (lower or standard case)
        # e.g. Folder: DG_collect_Dataset -> Script: DG_collect_dataset.py
        # We will handle this case-insensitive matching in Bash
        script_file = f"{app_name}.py" # Default guess
        is_folder = True

    repo_name = creds["deadlygraphics"]["repo_name"]
    workspace_root = os.path.expanduser(f"~/workspace/{repo_name}")
    
    if "DG_ScriptsBackup" in input_name:
        dest_folder = os.path.join(workspace_root, "ai", "scripts")
        is_app = False
    else:
        dest_folder = os.path.join(workspace_root, "ai", "apps", app_name)
        is_app = True

    gh_user = creds["github"]["user"]
    repo_url = f"https://github.com/{gh_user}/{repo_name}.git"

    bash_content = f"""#!/bin/bash
set -e
REPO_DIR="{workspace_root}"
DEST_DIR="{dest_folder}"
INPUT_NAME="{input_name}"
APP_NAME="{app_name}"
IS_APP="{str(is_app).lower()}"
IS_FOLDER="{str(is_folder).lower()}"

echo "--> Repo: $REPO_DIR"

# 1. Update Repo
if [ ! -d "$REPO_DIR" ]; then
    mkdir -p "$REPO_DIR"
    git clone "{repo_url}" "$REPO_DIR"
else
    if [ ! -d "$REPO_DIR/.git" ]; then
        mv "$REPO_DIR" "$REPO_DIR_BACKUP_$(date +%s)"
        git clone "{repo_url}" "$REPO_DIR"
    else
        cd "$REPO_DIR"
        git pull
    fi
fi

# 2. Install Logic (Folder vs File)
mkdir -p "$DEST_DIR"
SRC="$REPO_DIR/$INPUT_NAME"

if [ ! -e "$SRC" ]; then
    # Try case-insensitive finding if exact match fails
    SRC=$(find "$REPO_DIR" -maxdepth 1 -iname "$INPUT_NAME" | head -n 1)
fi

if [ -e "$SRC" ]; then
    echo "--> Installing from $SRC..."
    
    # Backup existing
    if [ -d "$DEST_DIR" ]; then
        # If it's a folder update, we Rsync or Copy
        # We create a backup of the WHOLE app folder
        if [ -e "$DEST_DIR/$INPUT_NAME" ] || [ "$(ls -A $DEST_DIR)" ]; then
             mkdir -p "$DEST_DIR/../old"
             tar -czf "$DEST_DIR/../old/$APP_NAME.$(date +%Y%m%d_%H%M%S).tar.gz" -C "$DEST_DIR" .
        fi
    fi

    if [ "$IS_FOLDER" == "true" ]; then
        # Copy CONTENTS of source folder to dest
        cp -r "$SRC/"* "$DEST_DIR/"
    else
        # Copy single file
        cp "$SRC" "$DEST_DIR/"
    fi
    
    chmod +x "$DEST_DIR"/*.py 2>/dev/null || true
else
    echo "❌ Error: '$INPUT_NAME' not found in repo root!"
    exit 1
fi

# 3. Configs
if [[ "$APP_NAME" == *"scraper"* ]]; then
    CHECKLIST="$DEST_DIR/scrapervideo_checklist.txt"
    if [ ! -f "$CHECKLIST" ]; then echo "# URLs here" > "$CHECKLIST"; fi
fi
if [[ "$APP_NAME" == *"dataset"* ]]; then
    CHECKLIST="$DEST_DIR/dataset_checklist.txt"
    if [ ! -f "$CHECKLIST" ]; then echo "# URLs here" > "$CHECKLIST"; fi
fi

# 4. Dependencies
if [[ "$IS_APP" == "true" ]]; then
    cd "$DEST_DIR"
    
    # System Deps (Interactive Sudo)
    echo "--> Checking System Dependencies..."
    sudo apt-get update > /dev/null
    sudo apt-get install -y python3 python3-pip python3-venv unzip wget ffmpeg > /dev/null

    # Browser Checks (Chrome/Opera) - Install if missing
    if ! command -v google-chrome &> /dev/null; then
        echo "--> Installing Chrome..."
        wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
        sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list'
        sudo apt-get update > /dev/null; sudo apt-get install -y google-chrome-stable > /dev/null
    fi
    
    # Venv
    if [ ! -d "venv" ]; then python3 -m venv venv; fi
    source venv/bin/activate
    
    echo "--> Updating Python Libs..."
    pip install --quiet --upgrade pip
    pip install --quiet setuptools wheel "blinker<1.8.0" webdriver-manager yt-dlp tqdm requests beautifulsoup4 selenium selenium-wire undetected-chromedriver Pillow

    # 5. Global Shortcut
    # Find the main script file. Priority: Exact match .py -> lowercase .py -> any .py
    MAIN_SCRIPT="$DEST_DIR/$INPUT_NAME"
    if [ "$IS_FOLDER" == "true" ]; then
        # Try to find the python entry point
        if [ -f "$DEST_DIR/$APP_NAME.py" ]; then MAIN_SCRIPT="$DEST_DIR/$APP_NAME.py"; 
        elif [ -f "$DEST_DIR/$(echo $APP_NAME | tr '[:upper:]' '[:lower:]').py" ]; then MAIN_SCRIPT="$DEST_DIR/$(echo $APP_NAME | tr '[:upper:]' '[:lower:]').py";
        fi
    fi

    if [ -f "$MAIN_SCRIPT" ]; then
        LAUNCHER="/usr/local/bin/$APP_NAME"
        echo "--> Creating launcher: $LAUNCHER"
        
        cat <<EOF > /tmp/$APP_NAME.launcher
#!/bin/bash
cd "$DEST_DIR"
source venv/bin/activate
python3 "$MAIN_SCRIPT" "\$@"
EOF
        chmod +x /tmp/$APP_NAME.launcher
        sudo mv /tmp/$APP_NAME.launcher "$LAUNCHER"
        sudo chmod +x "$LAUNCHER"
        echo "✅ Shortcut created! Run '$APP_NAME' from anywhere."
    fi
fi

echo "--> DONE!"
"""

    # Native Linux Execution
    temp_script = f"/tmp/dg_install_{app_name}.sh"
    try:
        with open(temp_script, "w") as f: f.write(bash_content)
        subprocess.run(["bash", temp_script], check=True)
        log("Update Successful", "SUCCESS")
    except Exception as e:
        log(f"Update Failed: {e}", "FAIL")
    finally:
        if os.path.exists(temp_script): os.remove(temp_script)

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
    parser.add_argument("--folder", dest="wsl_folder")
    args = parser.parse_args()

    if args.mode == "push": push_mode(args, creds)
    elif args.mode == "pull": pull_mode(args, creds)
    elif args.mode == "install": install_mode(args, creds)

if __name__ == "__main__":
    main()