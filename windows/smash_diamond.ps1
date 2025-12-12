# File: smash_diamond.ps1
# Usage: ./smash_diamond.ps1
# Requires: Run as Administrator.

$ErrorActionPreference = "Stop"
Write-Host "Yaup!!!!!" -ForegroundColor Green
Write-Host "Initializing Diamond Smashing Machine: SECURE MODE..." -ForegroundColor Cyan

# --- Configuration ---
$DistroName      = "Diamond-Stack"
$InstallDir      = "C:\WSL\$DistroName"
$UbuntuUrl       = "https://cloud-images.ubuntu.com/wsl/releases/24.04/current/ubuntu-noble-wsl-amd64-wsl.rootfs.tar.gz"
$TarFile         = "ubuntu-noble-wsl.tar.gz"
$CredsJsonPath   = "C:\credentials\credentials.json"
$BashScript      = "provision_stack.sh"

# --- 0. Pre-Flight Checks ---
if (-not (Test-Path $BashScript)) {
    Write-Host "CRITICAL ERROR: '$BashScript' is missing!" -ForegroundColor Red
    exit
}
if (-not (Test-Path $CredsJsonPath)) {
    Write-Host "CRITICAL ERROR: Credentials file missing at '$CredsJsonPath'." -ForegroundColor Red
    exit
}

# --- 1. Clean Slate Protocol ---
if (wsl --list --quiet | Select-String -Pattern $DistroName) {
    Write-Host "Distro '$DistroName' exists!" -ForegroundColor Yellow
    $response = Read-Host "Do you want to DELETE it and start fresh? (y/n)"
    if ($response -eq 'y') {
        wsl --unregister $DistroName
    } else {
        exit
    }
}

# --- 2. Download Ubuntu Image ---
if (-not (Test-Path $TarFile)) {
    Write-Host "Downloading Ubuntu 24.04..." -ForegroundColor Cyan
    try {
        Invoke-WebRequest -Uri $UbuntuUrl -OutFile $TarFile
    } catch {
        $Fallback = "https://cloud-images.ubuntu.com/wsl/releases/jammy/current/ubuntu-jammy-wsl-amd64-wsl.rootfs.tar.gz"
        Write-Host "Trying fallback URL..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $Fallback -OutFile $TarFile
    }
}

# --- 3. Create New WSL Instance ---
Write-Host "Creating WSL Instance..." -ForegroundColor Cyan
if (-not (Test-Path $InstallDir)) { New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null }
wsl --import $DistroName $InstallDir $TarFile

# --- 4. User Setup ---
Write-Host "Configuring user 'seanf'..." -ForegroundColor Cyan
# --cd ~ prevents H: drive mount errors
wsl -d $DistroName --cd ~ useradd -m -s /bin/bash seanf
wsl -d $DistroName --cd ~ usermod -aG sudo seanf
wsl -d $DistroName --cd ~ sh -c "echo 'seanf:diamond' | chpasswd"
wsl -d $DistroName --cd ~ sh -c "echo '[user]`ndefault=seanf' > /etc/wsl.conf"

# --- 5. JSON Credential Injection ---
Write-Host "Injecting Credentials..." -ForegroundColor Magenta
try {
    $json = Get-Content -Raw -Path $CredsJsonPath | ConvertFrom-Json
    $gitUser = $json.github.user
    $gitEmail = $json.github.email
    $gitToken = $json.github.token

    if ($gitUser -and $gitToken) {
        $wslCredLine = "https://${gitUser}:${gitToken}@github.com"
        $WslHome = "\\wsl.localhost\$DistroName\home\seanf"
        
        $wslCredLine | Out-File -FilePath "$WslHome\.git-credentials" -Encoding ascii
        
        wsl -d $DistroName -u seanf --cd ~ -- git config --global user.name "$gitUser"
        wsl -d $DistroName -u seanf --cd ~ -- git config --global user.email "$gitEmail"
        wsl -d $DistroName -u seanf --cd ~ -- git config --global credential.helper store
    } else {
        Write-Host "Error: JSON missing user/token." -ForegroundColor Red; exit
    }
} catch {
    Write-Host "Error parsing JSON." -ForegroundColor Red; exit
}

# --- 6. Launch Provisioning ---
Write-Host "Launching Provisioning Script..." -ForegroundColor Magenta

$WslScriptPath = "\\wsl.localhost\$DistroName\home\seanf\provision_stack.sh"
Copy-Item -Path $BashScript -Destination $WslScriptPath

# Fix line endings and permissions
wsl -d $DistroName -u seanf --cd ~ -- bash -c "sed -i 's/\r$//' ~/provision_stack.sh"
wsl -d $DistroName -u seanf --cd ~ -- bash -c "chmod +x ~/provision_stack.sh"

# Run it
wsl -d $DistroName -u seanf --cd ~ -- bash -c "~/provision_stack.sh"

Write-Host "=================================================" -ForegroundColor Green
Write-Host "Diamond Smashing Deployment Complete." -ForegroundColor Green
Write-Host "Run: wsl -d $DistroName" -ForegroundColor Yellow
Write-Host "================================================="