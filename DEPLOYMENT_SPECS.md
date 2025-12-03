# Deployment Specifications

## 1. Automation Workflow
Step 01: Windows (Host) - Read C:\AI\github_token.txt
Step 02: Windows (Host) - wsl --install -d Ubuntu
Step 03: Manual - User sets UNIX password
Step 04: Linux (Guest) - Run Golden Command
Step 05: Linux (Guest) - Symlink Models (ln -s /mnt/c/AI/models ComfyUI/models)
Step 06: Linux (Guest) - Launch (python main.py --listen)

## 2. Configuration Files
- wsl_starter.py: Host Orchestrator
- setup_config.sh: Guest Installer
- requirements.txt: Python Dependencies
