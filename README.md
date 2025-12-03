# DeadlyGraphics: Automated ComfyUI Deployment (WSL2)

This repository hosts the **One-Shot Orchestrator** for deploying a fully GPU-accelerated ComfyUI environment on Windows via WSL2 (Ubuntu).

## 🚀 Prerequisites
1. **GitHub Token:** You must have a text file at 'C:\AI\github_token.txt' containing **only** your GitHub Personal Access Token (starting with 'ghp_').
2. **Python:** Installed on Windows.
3. **WSL:** Enabled on Windows.

## 🛠 Usage
1. Download 'wsl_starter.py' from this repository to your Windows machine.
2. Open PowerShell as Admin.
3. Run: 'python wsl_starter.py'

## ⚙️ The Automation Flow
1. **Host (Windows):** Script reads your token from 'C:\AI\github_token.txt'.
2. **Host (Windows):** Installs/Launches Ubuntu.
3. **Manual Pause:** You enter your UNIX password in the new window.
4. **Guest (Linux):** You paste the 'Golden Command' provided by the script.
5. **Guest (Linux):** Script installs Git, CUDA, PyTorch, ComfyUI, links models from 'C:\AI\models', and launches.
