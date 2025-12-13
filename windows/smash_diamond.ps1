# =========================================================
# DIAMOND SMASHING MACHINE — NUCLEAR OPTION v5 (VERIFIED)
# =========================================================
# FIX: Ubuntu 24.04 does not have CUDA 12.4 in the repo.
#      Bumped System Toolkit to 12.6 (Backward Compatible).
# =========================================================

$ErrorActionPreference = "Stop"

# --- CONFIGURATION ---
$DistroName = "Diamond-Stack"
$InstallDir = "C:\WSL\$DistroName"
$UbuntuUrl  = "https://cloud-images.ubuntu.com/wsl/releases/24.04/current/ubuntu-noble-wsl-amd64-wsl.rootfs.tar.gz"
$TarFile    = "ubuntu-noble-wsl.tar.gz"

$LinuxUser  = "seanf"
$TempPass   = "diamond"
$InstallRoot= "/home/$LinuxUser/Diamond-Stack"

# Version Locks
$TorchCmd   = "torch==2.5.1+cu124 torchvision==0.20.1+cu124 torchaudio==2.5.1+cu124"
$TorchIndex = "https://download.pytorch.org/whl/cu124"

Write-Host "DIAMOND SMASHING MACHINE NUCLEAR v5 STARTING" -ForegroundColor Cyan

# ---------------------------------------------------------
# HELPER: The Nuclear Injector
# ---------------------------------------------------------
function Invoke-NuclearBash {
    param (
        [string]$ScriptContent,
        [string]$User = "root",
        [string]$Description = "Executing Payload"
    )
    Write-Host "Action: $Description..." -NoNewline
    
    # 1. Sanitize: Windows CRLF -> Linux LF
    $CleanScript = $ScriptContent.Replace("`r`n", "`n")
    
    # 2. Encode: UTF-16 String -> UTF-8 Bytes -> Base64 String
    $Bytes = [Text.Encoding]::UTF8.GetBytes($CleanScript)
    $Encoded = [Convert]::ToBase64String($Bytes)

    # 3. Detonate: Pipe safely into Bash
    wsl -d $DistroName -u $User -- bash -c "echo $Encoded | base64 -d | bash"
    
    if ($LASTEXITCODE -eq 0) { Write-Host " [OK]" -ForegroundColor Green }
    else { 
        Write-Host " [FAILED]" -ForegroundColor Red
        wsl -d $DistroName -u root -- cat /var/log/diamond_install.log
        exit 1 
    }
}

# ---------------------------------------------------------
# 1. CLEANUP AND INSTALL
# ---------------------------------------------------------
Write-Host "Wiping old distro..."
wsl --shutdown 2>$null
wsl --unregister $DistroName 2>$null
if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }

if (-not (Test-Path $TarFile)) {
    Write-Host "Downloading Ubuntu 24.04..."
    Invoke-WebRequest $UbuntuUrl -OutFile $TarFile
}

Write-Host "Importing WSL..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
wsl --import $DistroName $InstallDir $TarFile

# ---------------------------------------------------------
# 2. USER CREATION
# ---------------------------------------------------------
$UserTemplate = @'
set -e
export DEBIAN_FRONTEND=noninteractive

if ! id "{0}" &>/dev/null; then
    echo "Creating user {0}..."
    adduser --disabled-password --gecos "" {0}
    echo "{0}:{1}" | chpasswd
    usermod -aG sudo {0}
    
    # Sudoers without password
    echo "{0} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/{0}
    chmod 0440 /etc/sudoers.d/{0}
    
    # Set default WSL user
    printf "[user]\ndefault={0}\n" > /etc/wsl.conf
fi
'@

$UserPayload = $UserTemplate -f $LinuxUser, $TempPass

Invoke-NuclearBash -ScriptContent $UserPayload -User "root" -Description "Creating User"
wsl --terminate $DistroName

# ---------------------------------------------------------
# 3. SYSTEM PROVISIONING (CUDA 12.6)
# ---------------------------------------------------------
$SysTemplate = @'
set -e
export DEBIAN_FRONTEND=noninteractive
LOG=/var/log/diamond_install.log

echo "--- SYSTEM INSTALL START ---" | tee -a $LOG

# 1. Base Deps
echo "Installing Dependencies..." | tee -a $LOG
apt-get update -y
apt-get install -y wget git gnupg python3-pip python3-venv python3-dev build-essential \
                   ffmpeg libgl1 libglib2.0-0 software-properties-common

# 2. CUDA Toolkit 12.6 (UPDATED for 24.04)
if [ ! -d "/usr/local/cuda-12.6" ]; then
    echo "Installing NVIDIA Keyring..." | tee -a $LOG
    
    # Clean up any old keys
    rm -f /usr/share/keyrings/cuda-archive-keyring.gpg
    
    # Download 24.04 Keyring
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
    dpkg -i cuda-keyring_1.1-1_all.deb
    
    echo "Updating Apt..." | tee -a $LOG
    apt-get update
    
    echo "Installing CUDA Toolkit 12.6..." | tee -a $LOG
    # 24.04 only has 12.5 and 12.6. We use 12.6.
    apt-get install -y cuda-toolkit-12-6
    
    # Path Persistence
    echo 'export PATH=/usr/local/cuda/bin:$PATH' >> /home/{0}/.bashrc
    echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> /home/{0}/.bashrc
fi

# 3. Fix Ownership
chown -R {0}:{0} /home/{0}
'@

$SysPayload = $SysTemplate -f $LinuxUser

Invoke-NuclearBash -ScriptContent $SysPayload -User "root" -Description "Installing System and CUDA"

# ---------------------------------------------------------
# 4. APP STACK
# ---------------------------------------------------------
$AppTemplate = @'
set -e
mkdir -p {0}
cd {0}

# --- A. ComfyUI ---
if [ ! -d "ComfyUI" ]; then
    echo "Installing ComfyUI..."
    git clone https://github.com/comfyanonymous/ComfyUI.git
    cd ComfyUI
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install {1} --index-url {2}
    pip install -r requirements.txt
    # Manager
    cd custom_nodes
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git
    deactivate
    cd {0}
fi

# --- B. AI-Toolkit (Ostris) ---
if [ ! -d "ai-toolkit" ]; then
    echo "Installing AI-Toolkit..."
    git clone https://github.com/ostris/ai-toolkit.git
    cd ai-toolkit
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install {1} --index-url {2}
    pip install -r requirements.txt
    deactivate
    cd {0}
fi

# --- C. OneTrainer ---
if [ ! -d "OneTrainer" ]; then
    echo "Installing OneTrainer..."
    git clone https://github.com/Nerogar/OneTrainer.git
    cd OneTrainer
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
    cd {0}
fi
'@

$AppPayload = $AppTemplate -f $InstallRoot, $TorchCmd, $TorchIndex

Invoke-NuclearBash -ScriptContent $AppPayload -User $LinuxUser -Description "Provisioning AI Apps"

# ---------------------------------------------------------
# 5. FINAL CHECK
# ---------------------------------------------------------
Write-Host ""
Write-Host "DIAMOND STACK READY" -ForegroundColor Green
Write-Host "   User: $LinuxUser"
Write-Host "   Pass: $TempPass"
Write-Host "   Loc:  ~/Diamond-Stack"
Write-Host ""
Write-Host "GPU CHECK:"
wsl -d $DistroName -- nvidia-smi
Write-Host ""
Write-Host "DONE" -ForegroundColor Cyan