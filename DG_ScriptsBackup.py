import os
import sys
import shutil
import subprocess
import argparse
import json
from pathlib import Path

# --- Configuration ---
CREDENTIALS_FILE_PATH = r"C:\credentials\credentials.json"
DEFAULT_LOCAL_SCRIPT = r"H:\My Drive\AI\DG_videoscraper.py"

def log(message, level="INFO"):
    prefix = {"INFO": "[INFO]", "SUCCESS": "[DONE]", "ERROR": "[FAIL]", "WARN": "[WARN]"}
    try:
        print(f"{prefix.get(level, '')} {message}")
    except:
        print(f"[{level}] {message}")

def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE_PATH):
        log(f"Credentials file missing: {CREDENTIALS_FILE_PATH}", "ERROR")
        sys.exit(1)
    try:
        with open(CREDENTIALS_FILE_PATH, 'r') as f: return json.load(f)
    except Exception as e:
        log(f"Config Error: {e}", "ERROR"); sys.exit(1)

def run_command(command, cwd=None):
    try:
        subprocess.run(command, cwd=cwd, shell=True, check=True)
    except subprocess.CalledProcessError:
        log(f"Command failed: {command}", "ERROR"); sys.exit(1)

# --- PUSH MODE (Windows -> GitHub) ---
def push_mode(args, creds):
    log("STARTING PUSH: Windows -> GitHub...", "INFO")
    
    # Load Paths
    repo_path = Path(creds["deadlygraphics"]["paths"]["local_repo"])
    source_path = Path(args.file_path if args.file_path else DEFAULT_LOCAL_SCRIPT)
    target_name = args.target_name if args.target_name else source_path.name
    dest_path = repo_path / target_name

    if not source_path.exists():
        log(f"File not found: {source_path}", "ERROR"); sys.exit(1)

    # 1. Configure Remote
    user = creds["github"]["user"]
    repo = creds["deadlygraphics"]["repo_name"]
    token = creds["github"].get("token", "").strip()
    
    if token and "god" not in token.lower() and "XXX" not in token:
        repo_url = f"https://{token}@github.com/{user}/{repo}.git"
    else:
        repo_url = f"https://github.com/{user}/{repo}.git"

    if not repo_path.exists():
        run_command(f'git clone "{repo_url}" "{repo_path}"')

    # 2. Configure Identity
    email = creds["github"]["email"]
    run_command(f'git config user.email "{email}"', cwd=repo_path)
    run_command(f'git config user.name "{user}"', cwd=repo_path)
    run_command(f'git remote set-url origin "{repo_url}"', cwd=repo_path)

    # 3. Copy & Push
    shutil.copy2(source_path, dest_path)
    run_command(f'git add "{target_name}"', cwd=repo_path)
    
    status = subprocess.run('git status --porcelain', cwd=repo_path, capture_output=True, text=True, shell=True)
    if status.stdout.strip():
        run_command(f'git commit -m "Update {target_name}"', cwd=repo_path)
        run_command('git push origin main', cwd=repo_path)
        log(f"Successfully pushed {target_name} to GitHub!", "SUCCESS")
    else:
        log("No changes needed (file matches repo).", "WARN")

# --- PULL MODE (Trigger WSL to Pull from GitHub) ---
def install_mode(args, creds):
    # 1. Run the Push first
    push_mode(args, creds)
    print("-" * 40)
    
    log("STARTING WSL UPDATE: Pulling from GitHub...", "INFO")
    
    wsl_user = creds["deadlygraphics"]["wsl_user"]
    gh_user = creds["github"]["user"]
    repo_name = creds["deadlygraphics"]["repo_name"]
    
    # Where the repo lives inside WSL
    wsl_repo_root = f"/home/{wsl_user}/workspace/{repo_name}"
    
    # We use the public HTTPS url for pulling inside WSL to avoid token issues
    public_repo_url = f"https://github.com/{gh_user}/{repo_name}.git"

    # This BASH script runs INSIDE WSL
    # It does NOT look at Windows drives. It looks at GitHub.
    bash_commands = f"""
set -e
echo "--> Target: {wsl_repo_root}"

# 1. Ensure Directory Exists
if [ ! -d "{wsl_repo_root}" ]; then
    echo "--> Cloning repo from GitHub..."
    mkdir -p "{wsl_repo_root}"
    git clone "{public_repo_url}" "{wsl_repo_root}"
else
    echo "--> Pulling latest changes from GitHub..."
    cd "{wsl_repo_root}"
    git pull
fi

# 2. Setup Dependencies
cd "{wsl_repo_root}"
if [ ! -d "venv" ]; then
    echo "--> Creating Virtual Environment..."
    # Attempt to install venv if missing (might ask for password)
    python3 -m venv venv || (sudo apt-get update && sudo apt-get install -y python3-venv && python3 -m venv venv)
fi

source venv/bin/activate
echo "--> Installing Python Libraries..."
pip install --quiet --upgrade pip
pip install --quiet yt-dlp tqdm requests beautifulsoup4 selenium undetected-chromedriver selenium-wire

echo "--> WSL Sync Complete!"
"""

    # --- CRITICAL FIX ---
    # We strip Windows CR (\r) characters so Linux doesn't crash
    clean_bash = "\n".join(bash_commands.splitlines())

    try:
        # We run wsl.exe with --cd ~
        # This ensures it starts in the Linux Home, NOT on the H: drive.
        subprocess.run(
            ["wsl", "-u", wsl_user, "--cd", "~", "bash"], 
            input=clean_bash, 
            text=True, 
            encoding='utf-8', 
            check=True
        )
        log("WSL Update Finished Successfully", "SUCCESS")
    except subprocess.CalledProcessError:
        log("WSL Update Failed", "ERROR")

def main():
    creds = load_credentials()
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["push", "install"])
    parser.add_argument("file_path", nargs="?")
    parser.add_argument("--name", dest="target_name")
    args = parser.parse_args()

    if args.mode == "push": push_mode(args, creds)
    elif args.mode == "install": install_mode(args, creds)

if __name__ == "__main__":
    main()