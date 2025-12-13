# =========================================================
# 💎 DIAMOND SMASHING MACHINE — WINDOWS BOOTSTRAP 💎
# =========================================================
# Run from elevated PowerShell
# Usage: .\smash_diamond.ps1
# =========================================================

$ErrorActionPreference = "Stop"

$DistroName = "Diamond-Stack"
$InstallDir = "C:\WSL\$DistroName"
$UbuntuUrl  = "https://cloud-images.ubuntu.com/wsl/releases/24.04/current/ubuntu-noble-wsl-amd64-wsl.rootfs.tar.gz"
$TarFile    = "ubuntu-noble-wsl.tar.gz"

$LinuxUser  = "seanf"
$TempPass  = "diamond"

$CredsPath = "C:\credentials\credentials.json"
$RepoUrl   = "https://github.com/walshderek/deadlygraphics.git"
$RepoPath  = "/home/$LinuxUser/workspace/deadlygraphics"
$Provision = "$RepoPath/provision_stack.sh"

Write-Host "💎 DIAMOND SMASHING MACHINE STARTING 💎" -ForegroundColor Cyan

# ---------------------------------------------------------
# 1. Kill existing WSL
# ---------------------------------------------------------
Write-Host "🧨 Removing existing WSL distro (if present)..."
wsl --shutdown
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
# 3. Create WSL
# ---------------------------------------------------------
Write-Host "🐧 Creating WSL distro..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
wsl --import $DistroName $InstallDir $TarFile

# ---------------------------------------------------------
# 4. Create User
# ---------------------------------------------------------
Write-Host "👤 Creating Linux user '$LinuxUser'..."

wsl -d $DistroName -u root -- bash -c "
useradd -m -s /bin/bash $LinuxUser &&
echo '$LinuxUser:$TempPass' | chpasswd &&
usermod -aG sudo $LinuxUser &&
echo '$LinuxUser ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/$LinuxUser &&
chmod 0440 /etc/sudoers.d/$LinuxUser &&
echo '[user]
default=$LinuxUser' > /etc/wsl.conf
"

wsl --terminate $DistroName

# ---------------------------------------------------------
# 5. Inject GitHub Credentials
# ---------------------------------------------------------
if (Test-Path $CredsPath) {
    Write-Host "🔑 Injecting GitHub credentials..."

    $creds = Get-Content $CredsPath | ConvertFrom-Json
    $gitUrl = "https://$($creds.github.user):$($creds.github.token)@github.com"

    wsl -d $DistroName -u $LinuxUser -- bash -c "
git config --global credential.helper store &&
echo '$gitUrl' > ~/.git-credentials &&
git config --global user.name '$($creds.github.user)' &&
git config --global user.email '$($creds.github.email)'
"
}

# ---------------------------------------------------------
# 6. Verify GPU
# ---------------------------------------------------------
Write-Host "🎮 Verifying NVIDIA GPU passthrough..."
wsl -d $DistroName -- nvidia-smi

# ---------------------------------------------------------
# 7. Clone Repo
# ---------------------------------------------------------
Write-Host "📦 Cloning deadlygraphics repo..."
wsl -d $DistroName -u $LinuxUser -- bash -c "
mkdir -p ~/workspace &&
cd ~/workspace &&
git clone $RepoUrl deadlygraphics
"

# ---------------------------------------------------------
# 8. Provision Apps (Venv + CUDA)
# ---------------------------------------------------------
Write-Host "⚙️ Running provision_stack.sh..."
wsl -d $DistroName -u $LinuxUser -- bash -c "
cd ~/workspace/deadlygraphics &&
chmod +x provision_stack.sh &&
./provision_stack.sh
"

# ---------------------------------------------------------
# 9. Final Notice
# ---------------------------------------------------------
Write-Host ""
Write-Host "✅ DIAMOND STACK READY" -ForegroundColor Green
Write-Host "🔐 TEMP PASSWORD: diamond"
Write-Host "👉 PLEASE CHANGE YOUR PASSWORD NOW:"
Write-Host "   wsl -d $DistroName"
Write-Host "   passwd"
Write-Host ""
Write-Host "💎 DONE 💎" -ForegroundColor Cyan
