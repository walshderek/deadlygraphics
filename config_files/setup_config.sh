#!/bin/bash
set -e

# DEFINE CORRECT PATHS
WORKSPACE_ROOT="$HOME/workspace/deadlygraphics/ai/apps"
VENV_PATH="$WORKSPACE_ROOT/ai_env"
COMFY_PATH="$WORKSPACE_ROOT/ComfyUI"

echo "1/8: Installing System Dependencies..."
# CRITICAL FIX: Added python3-pip so venv creation actually includes pip
sudo apt update && sudo apt install -y python3-venv python3-pip git build-essential

echo "2/8: Creating Workspace & Virtual Environment..."
mkdir -p "$WORKSPACE_ROOT"
cd "$WORKSPACE_ROOT"

# Re-create venv if it exists to ensure pip is there
if [ -d "$VENV_PATH" ]; then
    echo "Reseting venv to ensure clean pip install..."
    rm -rf "$VENV_PATH"
fi
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

# Double-check pip is alive
python -m ensurepip --upgrade
python -m pip install --upgrade pip

echo "3/8: Installing PyTorch & Drivers..."
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo "4/8: Installing Requirements..."
if [ -f "$HOME/deadlygraphics/config_files/requirements.txt" ]; then
    python -m pip install -r "$HOME/deadlygraphics/config_files/requirements.txt"
else
    echo "requirements.txt not found, skipping."
fi

echo "5/8: Cloning ComfyUI..."
if [ -d "$COMFY_PATH" ]; then
    echo "ComfyUI already exists. Skipping clone."
else
    git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFY_PATH"
fi

echo "6/8: Linking Models (C:\AI\models -> ComfyUI)..."
rm -rf "$COMFY_PATH/models"
ln -s /mnt/c/AI/models "$COMFY_PATH/models"

echo "7/8: Setup Complete."
echo "Launch with: cd $COMFY_PATH && python main.py --listen"
