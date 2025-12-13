# =========================================================
# DIAMOND SMASHING MACHINE — ONE CLICK WSL BOOTSTRAP
# =========================================================
# Run from ELEVATED PowerShell
# =========================================================

$ErrorActionPreference = "Stop"

$DistroName = "Diamond-Stack"
$InstallDir = "C:\WSL\$DistroName"
$UbuntuUrl  = "https://cloud-images.ubuntu.com/wsl/releases/24.04/current/ubuntu-noble-wsl-amd64-wsl.rootfs.tar.gz"
$TarFile    = "ubuntu-noble-wsl.tar.gz"

$LinuxUser  = "seanf"
$TempPass  = "diamond"

$RepoUrl   = "https://github.com/walshderek/deadlygraphics.git"

Write-Host "💎 DIAMOND SMASHING MACHINE STARTING" -ForegroundColor Cyan

# ---------------------------------------------------------
# 1. Remove existing distro
# ---------------------------------------------------------
wsl --shutdown 2>$null
wsl --unregister $DistroName 2>$null

if (Test-Path $InstallDir) {
    Remove-Item -Recurse -Force $InstallDir
}

# ---------------------------------------------------------
# 2. Download Ubuntu
# ---------------------------------------------------------
if (-not (Test-Path $TarFile)) {
    Invoke-WebRequest $UbuntuUrl -OutFile $TarFile
}

# ---------------------------------------------------------
# 3. Import WSL
# ---------------------------------------------------------
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
wsl --import $DistroName $InstallDir $TarFile

# ---------------------------------------------------------
# 4. Create Linux user (SAFE: external bash script)
# ---------------------------------------------------------
$TmpScript = "$env:TEMP\dg_user_setup.sh"

@"
set -e

useradd -m -s /bin/bash $LinuxUser || true
echo '$LinuxUser:$TempPass' | chpasswd
usermod -aG sudo $LinuxUser

echo '$LinuxUser ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/$LinuxUser
chmod 0440 /etc/sudoers.d/$LinuxUser

printf "[user]\ndefault=$LinuxUser\n" > /etc/wsl.conf
"@ | Set-Content -Encoding UTF8 $TmpScript

wsl -d $DistroName -u root -- bash /mnt/c/Users/$env:USERNAME/AppData/Local/Temp/dg_user_setup.sh
wsl --terminate $DistroName

# ---------------------------------------------------------
# 5. Verify GPU passthrough
# ---------------------------------------------------------
Write-Host "🎮 Verifying GPU..."
wsl -d $DistroName -- nvidia-smi

# ---------------------------------------------------------
# 6. Clone repo
# ---------------------------------------------------------
wsl -d $DistroName -u $LinuxUser -- bash -c "
set -e
mkdir -p ~/workspace
cd ~/workspace
git clone $RepoUrl deadlygraphics
"

# ---------------------------------------------------------
# 7. Provision stack (venvs, CUDA, Torch)
# ---------------------------------------------------------
wsl -d $DistroName -u $LinuxUser -- bash -c "
set -e
cd ~/workspace/deadlygraphics
chmod +x provision_stack.sh
./provision_stack.sh
"

# ---------------------------------------------------------
# 8. Final message
# ---------------------------------------------------------
Write-Host ""
Write-Host "✅ DIAMOND STACK READY" -ForegroundColor Green
Write-Host "TEMP PASSWORD: diamond"
Write-Host "CHANGE IT NOW:"
Write-Host "  wsl -d $DistroName"
Write-Host "  passwd"
Write-Host ""
Write-Host "DONE" -ForegroundColor Cyan
