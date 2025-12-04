import os
import sys
import shutil
import subprocess
import argparse
import json
from pathlib import Path

# --- Configuration ---
# Pointing to your new centralized credentials file
CREDENTIALS_FILE_PATH = r"C:\credentials\credentials.json"

# Default script to act on if none provided
DEFAULT_LOCAL_SCRIPT = r"H:\My Drive\AI\DG_videoscraper.py"

def log(message, level="INFO"):
    prefix = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARN": "⚠️"}
    print(f"{prefix.get(level, '')} {message}")

def load_credentials():
    """Loads settings from the centralized JSON file."""
    if not os.path.exists(CREDENTIALS_FILE_PATH):
        log(f"Credentials file missing at: {CREDENTIALS_FILE_PATH}", "ERROR")
        log("Please create this file with your GitHub/Project details.", "ERROR")
        sys.exit(1)
    
    try:
        with open(CREDENTIALS_FILE_PATH, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log(f"Error reading JSON config: {e}", "ERROR")
        sys.exit(1)

def run_command(command, cwd=None, shell=False):
    """Runs a system command."""
    try:
        subprocess.run(command, cwd=cwd, shell=shell, check=True)
    except subprocess.CalledProcessError as e:
        log(f"Command failed: {e}", "ERROR")
        sys.exit(1)

def configure_git_identity(creds, repo_path):
    """Sets local git config using identity from credentials.json."""
    email = creds["github"].get("email")
    name = creds["github"].get("user")
    
    if email and name:
        run_command(["git", "config", "user.email", email], cwd=repo_path)
        run_command(["git", "config", "user.name", name], cwd=repo_path)

def get_remote_url(creds):
    """Constructs the remote URL, injecting the token if present."""
    user = creds["github"]["user"]
    # We assume 'deadlygraphics' implies the repo name in the config
    repo = creds["deadlygraphics"]["repo_name"]
    token = creds["github"].get("token", "").strip()
    
    if token and "god" not in token.lower(): # Basic check to ensure it's not a placeholder
        # Authenticated URL
        return f"https://{token}@github.com/{user}/{repo}.git"
    else:
        # Standard URL
        return f"https://github.com/{user}/{repo}.git"

def push_mode(args, creds):
    log("🚀 STARTING PUSH (Backup)", "INFO")

    # Access paths from the 'deadlygraphics' section
    repo_path = Path(creds["deadlygraphics"]["paths"]["local_repo"])
    
    # Source file logic
    if args.file_path:
        source_path = Path(args.file_path)
    else:
        source_path = Path(DEFAULT_LOCAL_SCRIPT)
        
    if not source_path.exists():
        log(f"File not found: {source_path}", "ERROR")
        sys.exit(1)

    target_name = args.target_name if args.target_name else source_path.name
    dest_path = repo_path / target_name

    log(f"Source: {source_path}", "INFO")
    log(f"Target Repo: {repo_path}", "INFO")

    # 1. Clone if repo doesn't exist
    repo_url = get_remote_url(creds)
    
    if not repo_path.exists():
        log(f"Repo missing. Cloning...", "WARN")
        run_command(["git", "clone", repo_url, str(repo_path)])
    
    # 2. Configure Identity
    configure_git_identity(creds, repo_path)
    
    # 3. Update Remote URL (Ensure token is fresh)
    log("Updating remote URL authentication...", "INFO")
    run_command(["git", "remote", "set-url", "origin", repo_url], cwd=repo_path)

    # 4. Copy File
    shutil.copy2(source_path, dest_path)

    # 5. Git Operations
    run_command(["git", "add", target_name], cwd=repo_path)
    
    # Check status
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True)
    
    if status.stdout.strip():
        commit_msg = f"Update {target_name}"
        run_command(["git", "commit", "-m", commit_msg], cwd=repo_path)
        run_command(["git", "push", "origin", "main"], cwd=repo_path)
        log(f"✅ Successfully pushed {target_name}!", "SUCCESS")
    else:
        log("No changes needed (file matches repo).", "WARN")

def install_mode(args, creds):
    log("🚀 STARTING INSTALL (WSL Sync)", "INFO")
    
    wsl_user = creds["deadlygraphics"]["wsl_user"]
    wsl_dir = creds["deadlygraphics"]["paths"]["wsl_app_dir"]
    
    # GitHub setup for WSL
    gh_user = creds["github"]["user"]
    repo_name = creds["deadlygraphics"]["repo_name"]
    # We use the public HTTP URL for pulling in WSL to avoid putting the token in bash history
    # unless it's a private repo, in which case we might need the token.
    repo_url = f"https://github.com/{gh_user}/{repo_name}.git"

    bash_setup = f"""
    set -e
    APP_DIR="{wsl_dir}"
    
    echo "--> Setting up $APP_DIR..."
    mkdir -p "$APP_DIR"
    cd "$APP_DIR"

    echo "--> Syncing GitHub..."
    if [ -d .git ]; then
        git pull
    else
        git clone "{repo_url}" .
    fi
    
    chmod +x *.py

    echo "--> Checking System Dependencies..."
    sudo apt-get update > /dev/null
    sudo apt-get install -y python3 python3-pip python3-venv unzip wget > /dev/null

    if ! command -v google-chrome &> /dev/null; then
        echo "   Installing Chrome (required for scrapers)..."
        wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
        sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list'
        sudo apt-get update > /dev/null
        sudo apt-get install -y google-chrome-stable > /dev/null
    fi

    echo "--> Updating Python Environment..."
    if [ ! -d "venv" ]; then python3 -m venv venv; fi
    source venv/bin/activate
    pip install --upgrade pip > /dev/null
    pip install yt-dlp tqdm requests beautifulsoup4 selenium undetected-chromedriver selenium-wire > /dev/null

    echo "✅ WSL Update Complete!"
    """
    
    try:
        subprocess.run(["wsl", "-u", wsl_user, "bash"], input=bash_setup, text=True, check=True)
    except subprocess.CalledProcessError:
        log("WSL installation failed.", "ERROR")

def main():
    # Load credentials first
    creds = load_credentials()

    parser = argparse.ArgumentParser(description="Deadly Graphics Manager")
    parser.add_argument("mode", choices=["push", "install"], help="Action to perform")
    parser.add_argument("file_path", nargs="?", help="Path to script (Required for push)")
    parser.add_argument("--name", dest="target_name", help="Custom filename in Repo")

    args = parser.parse_args()

    if args.mode == "push":
        push_mode(args, creds)
    elif args.mode == "install":
        install_mode(args, creds)

if __name__ == "__main__":
    main()