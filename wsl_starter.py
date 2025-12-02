import subprocess
import time
import os
import sys

# --- CONFIGURATION ---
DISTRO_NAME = "Ubuntu"
REPO_ROOT = "github.com/walshderek/deadlygraphics.git"
# PATH TO TOKEN ON WINDOWS HOST
# (Double backslashes needed for Python strings)
TOKEN_FILE_PATH = r"C:\AI\github_token.txt"

def get_token_from_file():
    """Reads the GitHub token from a local file on the Windows Host."""
    if not os.path.exists(TOKEN_FILE_PATH):
        print(f"\n[ERROR] Token file not found at: {TOKEN_FILE_PATH}")
        print("Please create this file and paste your 'ghp_...' token inside it.")
        return None
    
    try:
        with open(TOKEN_FILE_PATH, "r") as f:
            token = f.read().strip()
        if not token.startswith("ghp_"):
            print(f"[WARNING] Token in {TOKEN_FILE_PATH} does not start with 'ghp_'. Proceeding anyway...")
        return token
    except Exception as e:
        print(f"[ERROR] Could not read token file: {e}")
        return None

def main():
    print(f"--- DEADLYGRAPHICS ORCHESTRATOR ({DISTRO_NAME}) ---")
    print("OBJECTIVE: Full One-Shot Install of ComfyUI + Environment")
    
    # 1. Secure Token Retrieval
    print(f"\n[Security] Reading credentials from {TOKEN_FILE_PATH}...")
    token = get_token_from_file()
    
    if not token:
        print("Aborting: No valid token found.")
        input("Press Enter to exit...")
        sys.exit(1)
        
    print("[Security] Token loaded successfully.")

    # Construct the URL securely
    repo_url_auth = f"https://{token}@{REPO_ROOT}"

    # The Proven "Golden Command"
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
    print(f"\n[Step 1] Installing/Launching {DISTRO_NAME}...")
    subprocess.run(["wsl", "--install", "-d", DISTRO_NAME], check=False)

    # 3. The Mandatory Pause
    print("\n" + "!"*60)
    print("              CRITICAL INTERVENTION REQUIRED")
    print("!"*60)
    print("Microsoft forces a manual password setup for new Linux installs.")
    print("1. A new window has opened.")
    print("2. Enter username 'seanf' and your password.")
    print("3. Wait for the green 'seanf@...' prompt in that window.")
    print("!"*60)
    
    input("\nPress ENTER here once you have set your Linux password... ")

    # 4. Handover
    print(f"\n[Step 3] EXECUTE THE CONFIGURATION")
    print("Paste the following command block into your new Ubuntu terminal:")
    print("-" * 20 + " BEGIN BLOCK " + "-" * 20)
    print(guest_command)
    print("-" * 20 + " END BLOCK " + "-" * 20)
    print("\nOnce executed, ComfyUI will launch automatically.")

if __name__ == "__main__":
    main()
