import subprocess
import time
import os
import sys

# --- CONFIGURATION ---
DISTRO_NAME = "Ubuntu"
REPO_ROOT = "github.com/walshderek/deadlygraphics.git"
TOKEN_FILE_PATH = r"C:\AI\github_token.txt"

def get_token():
    try:
        if os.path.exists(TOKEN_FILE_PATH):
            with open(TOKEN_FILE_PATH, "r", encoding="utf-8-sig") as f:
                t = f.read().strip()
            if not t.isprintable():
                with open(TOKEN_FILE_PATH, "r", encoding="utf-8") as f:
                    t = f.read().strip()
            return t
    except:
        pass
    return None

def main():
    print(f"--- DEADLYGRAPHICS ORCHESTRATOR ({DISTRO_NAME}) ---")
    
    token = get_token()
    if not token:
        print(f"[ERROR] Token missing at {TOKEN_FILE_PATH}"); sys.exit(1)

    repo_url_auth = f"https://{token}@{REPO_ROOT}"
    
    guest_cmd = (
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

    print(f"\n[Step 1] Installing {DISTRO_NAME}...")
    print(">>> NOTE: This downloads ~1GB. It WILL take 5-15 minutes.")
    print(">>> PLEASE WAIT. DO NOT PRESS CTRL+C.")
    try:
        subprocess.run(["wsl", "--install", "-d", DISTRO_NAME], check=False)
    except KeyboardInterrupt:
        sys.exit(1)

    print("\n" + "!"*60)
    print("              CRITICAL INTERVENTION REQUIRED")
    print("!"*60)
    print("1. A new window has opened.")
    print("2. Enter username 'seanf' and your password.")
    print("3. Wait for the green 'seanf@...' prompt in that window.")
    print("!"*60)
    input("\nPress ENTER here once you have set your Linux password... ")

    print("\n" + "="*60)
    print("              PART 2: GUEST CONFIGURATION")
    print("="*60)
    print("INSTRUCTIONS:")
    print("1. Copy the COMMAND BLOCK below (between the dotted lines).")
    print("2. Paste it into your new Ubuntu Terminal window.")
    print("3. Press Enter.")
    print("="*60)
    
    print("\n" + "-" * 20 + " COMMAND BLOCK " + "-" * 20)
    print(guest_cmd)
    print("-" * 20 + " COMMAND BLOCK " + "-" * 20)

if __name__ == "__main__":
    main()
