import subprocess
import time
import os
import sys

# --- CONFIGURATION ---
DISTRO_NAME = "Ubuntu"
REPO_ROOT = "github.com/walshderek/deadlygraphics.git"
TOKEN_FILE_PATH = r"C:\AI\github_token.txt"

def get_token_from_file():
    if not os.path.exists(TOKEN_FILE_PATH):
        print(f"\n[ERROR] Token file not found at: {TOKEN_FILE_PATH}")
        return None
    try:
        # Handle BOM if present by trying utf-8-sig first
        with open(TOKEN_FILE_PATH, "r", encoding="utf-8-sig") as f:
            token = f.read().strip()
        # Fallback check
        if not token.isprintable():
             with open(TOKEN_FILE_PATH, "r", encoding="utf-8") as f:
                token = f.read().strip()
        
        if not token.startswith("ghp_"):
            print(f"[WARNING] Token does not start with 'ghp_'. Proceeding...")
        return token
    except Exception as e:
        print(f"[ERROR] Could not read token file: {e}")
        return None

def main():
    print(f"--- DEADLYGRAPHICS ORCHESTRATOR ({DISTRO_NAME}) ---")
    
    # 1. Secure Token Retrieval
    print(f"\n[Security] Reading credentials from {TOKEN_FILE_PATH}...")
    token = get_token_from_file()
    if not token: sys.exit(1)
    print("[Security] Token loaded.")

    repo_url_auth = f"https://{token}@{REPO_ROOT}"

    guest_command = (
        "sudo apt update && sudo apt install git -y && "
        "git config --global credential.helper \"/mnt/c/Program\\ Files/Git/mingw64/bin/git-credential-manager.exe\" && "
        f"git clone {repo_url_auth} ~/deadlygraphics && "
        "cd ~/deadlygraphics/config_files/ && "
        "chmod +x setup_config.sh && "
        "./setup_config.sh && "
        "source ai_env/bin/activate && "
        "cd ComfyUI && "
        "python main.py --listen"
    )

    # 2. Install/Launch WSL
    print(f"\n[Step 1] Installing {DISTRO_NAME}...")
    print(">>> NOTE: This downloads ~1GB. It WILL take 5-15 minutes.")
    print(">>> PLEASE WAIT. DO NOT PRESS CTRL+C.")
    try:
        subprocess.run(["wsl", "--install", "-d", DISTRO_NAME], check=False)
    except KeyboardInterrupt:
        print("\n\n[!] Install cancelled. Run 'wsl --unregister Ubuntu' to fix.")
        sys.exit(1)

    # 3. The Pause
    print("\n" + "!"*60)
    print("              CRITICAL INTERVENTION REQUIRED")
    print("!"*60)
    print("1. Enter username 'seanf' and your password in the new window.")
    print("2. Wait for the green 'seanf@...' prompt.")
    print("!"*60)
    
    input("\nPress ENTER here once you have set your Linux password... ")

    # 4. Handover
    print(f"\n[Step 3] PASTE THIS INTO UBUNTU:")
    print("-" * 20 + " BEGIN BLOCK " + "-" * 20)
    print(guest_command)
    print("-" * 20 + " END BLOCK " + "-" * 20)

if __name__ == "__main__":
    main()
