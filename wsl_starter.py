import subprocess
import os
import time
from pathlib import Path

# --- CONFIGURATION ---
GITHUB_REPO = "walshderek/deadlygraphics"
WSL_DISTRO_NAME = "Ubuntu-AI-V002"
CONFIG_SCRIPT_NAME = "setup_config.sh"

def run_powershell(command):
    """Runs a command in Windows PowerShell and streams output."""
    print(f"\n[HOST] Executing: {command}")
    try:
        process = subprocess.run(["powershell", "-Command", command],
                                   capture_output=True,
                                   text=True,
                                   encoding='utf-8')
        print(process.stdout)

        # We only print errors if they aren't the expected 'distro not found' error
        if process.returncode != 0 and "No installed distributions" not in process.stderr:
            if "WSL_E_DISTRO_NOT_FOUND" not in process.stderr:
                print(f"[ERROR] PowerShell failed (Code {process.returncode}): {process.stderr}")

    except Exception as e:
        print(f"[FATAL ERROR] Failed to run PowerShell command: {e}")
        exit(1)

def main():
    global USER_NAME, GITHUB_TOKEN

    print("--- 🚀 V002 WSL AI STARTER: Setup Orchestration ---")

    # 1. User Input & Token Management
    print("\n--- 1. User Input (Part 1/2) ---")
    USER_NAME = input("Enter your desired Linux username (e.g., seanf): ")
    if not USER_NAME:
        print("Username cannot be empty. Exiting.")
        exit(1)

    GITHUB_TOKEN = input("Enter your GitHub Personal Access Token (for cloning/auth): ")
    if not GITHUB_TOKEN:
        print("Token cannot be empty. Exiting.")
        exit(1)

    # --- The Final Working Command Block (Printed first for safety) ---
    final_setup_command = (
        f'sudo apt update && sudo apt install git -y && '
        f'git config --global credential.helper "/mnt/c/Program\\ Files/Git/mingw64/bin/git-credential-manager.exe" && '
        f'git clone https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git /home/{USER_NAME}/deadlygraphics && '
        f'cd /home/{USER_NAME}/deadlygraphics/config_files/ && '
        f'./{CONFIG_SCRIPT_NAME}'
    )

    print("\n###################################################################################")
    print(">>> PART 2: CONFIGURATION COMMAND <<<")
    print("1. After setting the password, COPY and PASTE the following command EXACTLY:")
    print("-----------------------------------------------------------------------------------")
    print(f"{final_setup_command}")
    print("-----------------------------------------------------------------------------------")
    print("2. The script will now proceed with installation (Part 1/2).")
    print("###################################################################################")

    # 2. WSL Management & Installation
    print("\n--- 2. WSL Termination & Installation (Part 1/2) ---")
    run_powershell(f"wsl --terminate {WSL_DISTRO_NAME}")
    run_powershell(f"wsl --unregister {WSL_DISTRO_NAME}")

    # Install the new distribution (Requires manual first-time login/password setup)
    print(f"\n[HOST] Installing new distribution: {WSL_DISTRO_NAME}. YOU MUST SET THE PASSWORD NOW. The script will wait.")
    subprocess.run(["wsl", "--install", "--distribution", "Ubuntu", "--name", WSL_DISTRO_NAME], check=True)

    # 3. Final instructions for the user after the script loses control
    print("\n✅ ORCHESTRATION COMPLETE. The terminal is now waiting for you to paste the command above.")


if __name__ == "__main__":
    main()
