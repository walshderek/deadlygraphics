# =========================================================
# 💎 DIAMOND SMASHING MACHINE — WINDOWS BOOTSTRAP V2.1 💎
# =========================================================

$ErrorActionPreference = "Stop"

# ---------------- CONFIG ----------------
$DistroName = "Diamond-Stack"
$InstallDir = "C:\WSL\$DistroName"

$UbuntuUrl  = "https://cloud-images.ubuntu.com/wsl/releases/24.04/current/ubuntu-noble-wsl-amd64-wsl.rootfs.tar.gz"
$TarFile    = "ubuntu-noble-wsl.tar.gz"

$LinuxUser  = "seanf"
$TempPass   = "diamond"

$CredsPath  = "C:\credentials\credentials.json"
$RepoUrl    = "https://github.com/walshderek/deadlygraphics.git"
$WinModels  = "/mnt/c/AI/models"
# ----------------------------------------

Write-Host "💎 DIAMOND SMASHING MACHINE STARTING 💎" -ForegroundColor Cyan

# ---------------------------------------------------------
# 1. Remove existing WSL
# ---------------------------------------------------------
Write-Host "🧨 Removing existing WSL distro..."
wsl --shutdown 2>$null
wsl --unregister $DistroName 2>$null

if (Test-Path $InstallDir) {
    Remove-Item -Recurse -Force $InstallDir
}

# ---------------------------------------------------------
# 2. Download Ubuntu
# ---------------------------------------------------------
if (-not (Test-Path $TarFile)) {
    Write-Host "⬇️ Downloading Ubuntu 24.04..."
    Invoke-WebRequest $UbuntuUrl -OutFile $TarFile
}

# ---------------------------------------------------------
# 3. Import WSL
# ---------------------------------------------------------
Write-Host "🐧 Creating WSL distro..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
wsl --import $DistroName $InstallDir $TarFile

# ---------------------------------------------------------
# 4. Create Linux user (SAFE)
# ---------------------------------------------------------
Write-Host "👤 Creating Linux user..."

# STOP: The closing "@ below must be flush left!
$UserScript = @"
set -e
useradd -m -s /bin/bash $LinuxUser || true
echo '$LinuxUser'':'$TempPass | chpasswd
usermod -aG sudo $LinuxUser
echo '$LinuxUser ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/$LinuxUser
chmod 0440 /etc/sudoers.d/$LinuxUser
printf '[user]\ndefault=$LinuxUser\n' > /etc/wsl.conf
"@

wsl -d $DistroName -u root -- bash -c "$UserScript"
wsl --terminate $DistroName

# ---------------------------------------------------------
# 5. Inject GitHub credentials (optional)
# ---------------------------------------------------------
if (Test-Path $CredsPath) {
    Write-Host "🔑 Injecting GitHub credentials..."
    $creds = Get-Content $CredsPath | ConvertFrom-Json
    $gitUrl = "https://$($creds.github.user):$($creds.github.token)@github.com"

# STOP: The closing "@ below must be flush left!
$GitScript = @"
git config --global credential.helper store
echo '$gitUrl' > ~/.git-credentials
git config --global user.name '$($creds.github.user)'
git config --global user.email '$($creds.github.email)'
"@

    wsl -d $DistroName -u $LinuxUser -- bash -c "$GitScript"
}

# ---------------------------------------------------------
# 6. Verify GPU
# ---------------------------------------------------------
Write-Host "🎮 Verifying NVIDIA GPU passthrough..."
wsl -d $DistroName -- nvidia-smi

# ---------------------------------------------------------
# 7. System Prep & Model Linking (The "Pre-Launch" Phase)
# ---------------------------------------------------------
Write-Host "🏗️ Installing System Dependencies & Linking Models..."

# STOP: The closing "@ below must be flush left!
$SystemPrep = @"
set -e
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev build-essential git libgl1 libglib2.0-0 libtcmalloc-minimal4

# Create workspace structure
mkdir -p ~/workspace/deadlygraphics/ai/apps

# Link Global Models if they exist on Windows
if [ -d "$WinModels" ]; then
    echo "🔗 Linking Global Models..."
    mkdir -p ~/workspace/deadlygraphics/models
    # Remove directory if empty to allow link, or skip if populated
    if [ -d ~/workspace/deadlygraphics/models ] && [ ! -L ~/workspace/deadlygraphics/models ]; then
         rmdir ~/workspace/deadlygraphics/models 2>/dev/null || true
    fi
    if [ ! -e ~/workspace/deadlygraphics/models ]; then
        ln -s "$WinModels" ~/workspace/deadlygraphics/models
        echo "✅ Linked $WinModels -> models"
    fi
fi
"@

wsl -d $DistroName -u $LinuxUser -- bash -c "$SystemPrep"

# ---------------------------------------------------------
# 8. Inject DG_Launcher.py
# ---------------------------------------------------------
Write-Host "💉 Injecting DG_Launcher.py..."

# NOTE: We use @' (single quote) for Python code to prevent PowerShell variable expansion.
# STOP: The closing '@ below must be flush left!
$LauncherPy = @'
#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# --- CONFIGURATION ---
WORKSPACE_DIR = Path.home() / "workspace" / "deadlygraphics"
APPS_DIR = WORKSPACE_DIR / "ai" / "apps"
LOG_DIR = Path.home() / ".dg_logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / f"dg_launcher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# --- LOCKED VERSIONS (FROM TSV) ---
TORCH_CMD = (
    "torch==2.5.1+cu124 "
    "torchvision==0.20.1+cu124 "
    "torchaudio==2.5.1+cu124"
)
TORCH_INDEX = "--index-url https://download.pytorch.org/whl/cu124"

APPS = {
    "ComfyUI": {
        "repo": "https://github.com/comfyanonymous/ComfyUI.git",
        "path": "ComfyUI",
        "requirements": "requirements.txt"
    },
    "OneTrainer": {
        "repo": "https://github.com/Nerogar/OneTrainer.git",
        "path": "OneTrainer",
        "requirements": "requirements.txt"
    },
    "AI-Toolkit": {
        "repo": "https://github.com/ostris/ai-toolkit.git",
        "path": "AI-Toolkit",
        "requirements": "requirements.txt"
    },
    "DG_collect_dataset": {
        "repo": "https://github.com/walshderek/deadlygraphics.git",
        "path": "DG_collect_dataset",
        "requirements": "ai/apps/DG_collect_dataset/requirements.txt"
    },
    "DG_videoscraper": {
        "repo": "https://github.com/walshderek/deadlygraphics.git",
        "path": "DG_videoscraper",
        "requirements": "ai/apps/DG_videoscraper/requirements.txt"
    }
}

# ---------------- UTIL ----------------

def log(msg):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")

def run(cmd, cwd=None):
    log(f"💎 EXEC: {cmd}")
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)

# ---------------- GUARDS ----------------

def assert_cuda_present():
    try:
        subprocess.run(["nvidia-smi"], check=True, stdout=subprocess.DEVNULL)
        log("✅ NVIDIA driver detected")
    except Exception:
        log("❌ NVIDIA driver / CUDA not available. Provisioning is broken.")
        sys.exit(1)

def assert_python():
    log(f"🐍 Python: {sys.version.split()[0]} ({sys.executable})")

# ---------------- VENV ----------------

def ensure_venv(app_path: Path):
    venv_path = app_path / ".venv"
    if not venv_path.exists():
        log(f"🛠️ Creating venv: {venv_path}")
        run(f"python3 -m venv {venv_path}")
    return venv_path

# ---------------- INSTALL ----------------

def install_app(name, config):
    app_path = APPS_DIR / config["path"]

    # Clone
    if not app_path.exists():
        log(f"⬇️ Cloning {name}")
        run(f"git clone {config['repo']} {app_path}")

    # Venv
    venv = ensure_venv(app_path)
    pip = venv / "bin" / "pip"
    python = venv / "bin" / "python"

    # Pip upgrade
    run(f"{pip} install --upgrade pip wheel")

    # Torch (STRICT, GPU)
    log(f"🔥 Installing Torch (cu124) for {name}")
    run(f"{pip} install {TORCH_CMD} {TORCH_INDEX}")

    # GPU assert
    run(
        f"""{python} - << 'EOF'
import torch, sys
assert torch.cuda.is_available(), "CUDA NOT AVAILABLE"
print("✅ GPU OK:", torch.cuda.get_device_name(0))
print("Torch:", torch.__version__)
print("CUDA:", torch.version.cuda)
EOF"""
    )

    # Requirements
    req = app_path / config["requirements"]
    if not req.exists():
        req = WORKSPACE_DIR / config["requirements"]

    if req.exists():
        log(f"📦 Installing requirements for {name}")
        run(f"{pip} install -r {req}", cwd=app_path)
    else:
        log(f"⚠️ No requirements.txt for {name}")

# ---------------- MAIN ----------------

def main():
    if "--install" not in sys.argv:
        log("Usage: python3 DG_Launcher.py --install")
        sys.exit(1)

    assert_python()
    assert_cuda_present()

    APPS_DIR.mkdir(parents=True, exist_ok=True)

    for name, config in APPS.items():
        log(f"\n=== {name} ===")
        install_app(name, config)

    log("\n💎 DIAMOND SMASHING COMPLETE 💎")
    log(f"📄 Log written to: {LOG_FILE}")

if __name__ == "__main__":
    main()
'@

# Save to temp file in Windows then copy to WSL to avoid UNC path issues
$TempLauncher = "$env:TEMP\DG_Launcher.py"
$LauncherPy | Out-File -FilePath $TempLauncher -Encoding UTF8

Write-Host "📂 Moving Launcher to WSL..."
wsl -d $DistroName -u $LinuxUser -- bash -c "mkdir -p ~/workspace"
wsl -d $DistroName -u $LinuxUser -- bash -c "cp /mnt/c/Users/$($env:USERNAME)/AppData/Local/Temp/DG_Launcher.py ~/workspace/DG_Launcher.py"
wsl -d $DistroName -u $LinuxUser -- bash -c "sed -i 's/\r$//' ~/workspace/DG_Launcher.py"

# ---------------------------------------------------------
# 9. EXECUTE LAUNCHER
# ---------------------------------------------------------
Write-Host "🚀 Launching Python Provisioner..."
wsl -d $DistroName -u $LinuxUser -- bash -c "python3 ~/workspace/DG_Launcher.py --install"

# ---------------------------------------------------------
# 10. Final message
# ---------------------------------------------------------
Write-Host ""
Write-Host "✅ DIAMOND STACK READY" -ForegroundColor Green
Write-Host "🔐 TEMP PASSWORD: diamond"
Write-Host "👉 CHANGE IT NOW:"
Write-Host "   wsl -d $DistroName"
Write-Host "   passwd"
Write-Host ""
Write-Host "DONE" -ForegroundColor Cyan