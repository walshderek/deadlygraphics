# =========================================================
# 💎 DIAMOND SMASHING MACHINE — WINDOWS BOOTSTRAP 💎
# =========================================================

$ErrorActionPreference = "Stop"

# ---------------- CONFIG ----------------
$DistroName = "Diamond-Stack"
$InstallDir = "C:\WSL\$DistroName"

$UbuntuUrl  = "https://cloud-images.ubuntu.com/wsl/releases/24.04/current/ubuntu-noble-wsl-amd64-wsl.rootfs.tar.gz"
$TarFile    = "ubuntu-noble-wsl.tar.gz"

$LinuxUser  = "seanf"
$TempPass  = "diamond"

$CredsPath = "C:\credentials\credentials.json"
$RepoUrl   = "https://github.com/walshderek/deadlygraphics.git"
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
# 7. Clone repo
# ---------------------------------------------------------
Write-Host "📦 Cloning deadlygraphics..."
wsl -d $DistroName -u $LinuxUser -- bash -c "
mkdir -p ~/workspace &&
cd ~/workspace &&
git clone $RepoUrl deadlygraphics
"

# ---------------------------------------------------------
# 8. Provision stack
# ---------------------------------------------------------
Write-Host "⚙️ Running provision_stack.sh..."
wsl -d $DistroName -u $LinuxUser -- bash -c "
cd ~/workspace/deadlygraphics &&
chmod +x provision_stack.sh &&
./provision_stack.sh
"

# ---------------------------------------------------------
# 9. Final message
# ---------------------------------------------------------
Write-Host ""
Write-Host "✅ DIAMOND STACK READY" -ForegroundColor Green
Write-Host "🔐 TEMP PASSWORD: diamond"
Write-Host "👉 CHANGE IT NOW:"
Write-Host "   wsl -d $DistroName"
Write-Host "   passwd"
Write-Host ""
Write-Host "DONE" -ForegroundColor Cyan
