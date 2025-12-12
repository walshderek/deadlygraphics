#!/bin/bash
set -e

# --- Configuration ---
PYTHON_VER="3.11"
WORKSPACE_ROOT="$HOME/workspace/deadlygraphics/ai/apps"
USER_PASS="diamond" # Matches the password set in the PowerShell script

# HTTPS URLs - credentials will be injected by the PowerShell script
declare -A REPOS=(
    ["DG_vibecoder"]="https://github.com/deadlygraphics/DG_vibecoder.git"
    ["ComfyUI"]="https://github.com/comfyanonymous/ComfyUI.git"
    ["OneTrainer"]="https://github.com/Nerogar/OneTrainer.git"
    ["ai-toolkit"]="https://github.com/ostris/ai-toolkit.git"
    ["musubi-tuner"]="https://github.com/sdbds/musubi-tuner-scripts.git"
    ["video-scraper"]="https://github.com/deadlygraphics/video-scraper.git"
    ["dg_collect_dataset"]="https://github.com/deadlygraphics/dg_collect_dataset.git"
)

echo "================================================="
echo "💎 DIAMOND SMASHING MACHINE: PROVISIONING 💎"
echo "================================================="

# Helper to run sudo with password
run_sudo() {
    echo "$USER_PASS" | sudo -S "$@"
}

echo "Step 1: System Dependencies..."
# We use run_sudo to pass the password legitimately
run_sudo apt-get update
run_sudo apt-get upgrade -y
run_sudo apt-get install -y wget curl git build-essential software-properties-common libgl1 libglib2.0-0 python3-tk

echo "Step 2: Installing Python $PYTHON_VER..."
run_sudo add-apt-repository ppa:deadsnakes/ppa -y
run_sudo apt-get update
run_sudo apt-get install -y python$PYTHON_VER python$PYTHON_VER-venv python$PYTHON_VER-dev python3-pip

echo "Step 3: Cloning Repositories..."
mkdir -p "$WORKSPACE_ROOT"
cd "$WORKSPACE_ROOT"

for app in "${!REPOS[@]}"; do
    url="${REPOS[$app]}"
    if [ ! -d "$app" ]; then
        echo "⬇️ Cloning $app..."
        git clone "$url" "$app"
    else
        echo "✅ $app exists."
    fi
done

setup_venv() {
    local app_dir=$1
    local req_file=$2
    local extra_cmds=$3
    if [ -d "$app_dir" ]; then
        echo "🛠️ Configuring: $(basename "$app_dir")"
        cd "$app_dir"
        if [ ! -d ".venv" ]; then python$PYTHON_VER -m venv .venv; fi
        source .venv/bin/activate
        pip install --upgrade pip wheel
        if [ ! -z "$extra_cmds" ]; then eval "$extra_cmds"; fi
        if [ -f "$req_file" ]; then pip install -r "$req_file"; fi
        deactivate
        cd "$WORKSPACE_ROOT"
    fi
}

# --- Tool Setup ---
setup_venv "$WORKSPACE_ROOT/ComfyUI" "requirements.txt" "pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu124"
setup_venv "$WORKSPACE_ROOT/OneTrainer" "requirements.txt" "pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu124"
setup_venv "$WORKSPACE_ROOT/ai-toolkit" "requirements.txt" "pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu124"

if [ -d "$WORKSPACE_ROOT/musubi-tuner" ]; then
    cd "$WORKSPACE_ROOT/musubi-tuner"
    git submodule update --init --recursive
    cd "$WORKSPACE_ROOT"
    setup_venv "$WORKSPACE_ROOT/musubi-tuner" "requirements.txt" "pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu124"
fi

setup_venv "$WORKSPACE_ROOT/DG_vibecoder" "requirements.txt" ""
setup_venv "$WORKSPACE_ROOT/dg_collect_dataset" "requirements.txt" ""
setup_venv "$WORKSPACE_ROOT/video-scraper" "requirements.txt" ""

echo "💎 DONE. 💎"