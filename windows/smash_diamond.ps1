# File: smash_diamond.ps1
# Usage: ./smash_diamond.ps1
# Requires: Run as Administrator.

$ErrorActionPreference = "Stop"
Write-Host "Yaup!!!!!" -ForegroundColor Green
Write-Host "Initializing Diamond Smashing Machine: FINAL AUTO-GEN..." -ForegroundColor Cyan

# --- Configuration ---
$DistroName      = "Diamond-Stack"
$InstallDir      = "C:\WSL\$DistroName"
$UbuntuUrl       = "https://cloud-images.ubuntu.com/wsl/releases/24.04/current/ubuntu-noble-wsl-amd64-wsl.rootfs.tar.gz"
$TarFile         = "ubuntu-noble-wsl.tar.gz"
$CredsJsonPath   = "C:\credentials\credentials.json"
$BashScript      = "provision_stack.sh"
$LauncherFile    = "DG_Launcher.py"

# --- 0. Pre-Flight Checks ---
if (-not (Test-Path $BashScript)) { Write-Error "MISSING FILE: $BashScript"; exit }
if (-not (Test-Path $CredsJsonPath)) { Write-Error "MISSING FILE: $CredsJsonPath"; exit }

# --- 1. NUCLEAR OPTION: Force WIPE ---
Write-Host "Cleaning up old instances..." -ForegroundColor Yellow
wsl --unregister $DistroName 2>$null
if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }

# --- 2. Download Ubuntu ---
if (-not (Test-Path $TarFile)) {
    Write-Host "Downloading Ubuntu 24.04..." -ForegroundColor Cyan
    try {
        Invoke-WebRequest -Uri $UbuntuUrl -OutFile $TarFile
    } catch {
        $Fallback = "https://cloud-images.ubuntu.com/wsl/releases/jammy/current/ubuntu-jammy-wsl-amd64-wsl.rootfs.tar.gz"
        Write-Host "Using fallback URL..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $Fallback -OutFile $TarFile
    }
}

# --- 3. Create WSL Instance ---
Write-Host "Creating fresh WSL Instance..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
wsl --import $DistroName $InstallDir $TarFile

# --- 4. User Setup (Root) ---
Write-Host "Configuring user 'seanf'..." -ForegroundColor Cyan
wsl -d $DistroName -u root --cd ~ useradd -m -s /bin/bash seanf
wsl -d $DistroName -u root --cd ~ usermod -aG sudo seanf
wsl -d $DistroName -u root --cd ~ sh -c "echo 'seanf:diamond' | chpasswd"
# Enable Passwordless Sudo
wsl -d $DistroName -u root --cd ~ sh -c "echo 'seanf ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/seanf"
wsl -d $DistroName -u root --cd ~ sh -c "chmod 0440 /etc/sudoers.d/seanf"
# Set default user
wsl -d $DistroName -u root --cd ~ sh -c "echo '[user]`ndefault=seanf' > /etc/wsl.conf"

# --- 5. Credentials Injection (Linux Native) ---
Write-Host "Injecting Credentials..." -ForegroundColor Magenta
try {
    $jsonContent = Get-Content -Raw -Path $CredsJsonPath
    $json = $jsonContent | ConvertFrom-Json
    $gitUser  = $json.github.user
    $gitEmail = $json.github.email
    $gitToken = $json.github.token

    if ($gitUser -and $gitToken) {
        $credContent = "https://${gitUser}:${gitToken}@github.com"
        wsl -d $DistroName -u seanf --cd ~ -- sh -c "echo '$credContent' > ~/.git-credentials"
        wsl -d $DistroName -u seanf --cd ~ -- chmod 600 ~/.git-credentials
        wsl -d $DistroName -u seanf --cd ~ -- git config --global user.name "$gitUser"
        wsl -d $DistroName -u seanf --cd ~ -- git config --global user.email "$gitEmail"
        wsl -d $DistroName -u seanf --cd ~ -- git config --global credential.helper store
    } else {
        Write-Error "JSON missing user or token."
    }
} catch {
    Write-Error "Failed to parse credentials file: $_"
}

# --- 6. Launch Provisioning ---
Write-Host "Running Provisioning Script..." -ForegroundColor Magenta
$WslScriptPath = "\\wsl.localhost\$DistroName\home\seanf\provision_stack.sh"
Copy-Item -Path $BashScript -Destination $WslScriptPath

wsl -d $DistroName -u root --cd ~ -- bash -c "chown seanf:seanf /home/seanf/provision_stack.sh"
wsl -d $DistroName -u seanf --cd ~ -- bash -c "sed -i 's/\r$//' ~/provision_stack.sh"
wsl -d $DistroName -u seanf --cd ~ -- bash -c "chmod +x ~/provision_stack.sh"
wsl -d $DistroName -u seanf --cd ~ -- bash -c "~/provision_stack.sh"

# --- 7. AUTO-GENERATE LAUNCHER ---
Write-Host "Generating DG_Launcher.py..." -ForegroundColor Cyan
$LauncherContent = @"
import subprocess
import sys
import argparse

DISTRO_NAME = "Diamond-Stack"
# Updated path based on your specific repo structure
WS_ROOT = "~/workspace/deadlygraphics/ai/apps"

APPS = {
    "comfy": {
        "dir": f"{WS_ROOT}/DG_vibecoder/apps_managed/ComfyUI",
        "cmd": ".venv/bin/python main.py --listen 0.0.0.0 --port 8188",
        "desc": "ComfyUI"
    },
    "onetrainer": {
        "dir": f"{WS_ROOT}/OneTrainer",
        "cmd": ".venv/bin/python main.py",
        "desc": "OneTrainer"
    },
    "vibecoder": {
        "dir": f"{WS_ROOT}/DG_vibecoder",
        "cmd": ".venv/bin/python DG_vibecoder.py",
        "desc": "DG Vibecoder"
    }
}

def run(app_key):
    app = APPS.get(app_key)
    if not app:
        print(f"Unknown app: {app_key}")
        return
    print(f"💎 Launching {app['desc']}...")
    bash_cmd = f"cd {app['dir']} && {app['cmd']}"
    try:
        subprocess.run(["wsl", "-d", DISTRO_NAME, "--cd", "~", "bash", "-c", bash_cmd])
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("app", nargs="?", default="list")
    args = parser.parse_args()
    if args.app == "list":
        for k in APPS: print(f"- {k}")
    else:
        run(args.app.lower())
"@

$LauncherContent | Out-File -FilePath $LauncherFile -Encoding ascii

Write-Host "=================================================" -ForegroundColor Green
Write-Host "Diamond Smashing Complete." -ForegroundColor Green
Write-Host "Launcher created: $LauncherFile" -ForegroundColor Yellow
Write-Host "Try: python $LauncherFile comfy" -ForegroundColor White
Write-Host "================================================="