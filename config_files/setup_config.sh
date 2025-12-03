#!/bin/bash
set -e

# DEFINE CORRECT PATHS
WORKSPACE_ROOT="$HOME/workspace/deadlygraphics/ai/apps"
VENV_PATH="$WORKSPACE_ROOT/ai_env"
COMFY_PATH="$WORKSPACE_ROOT/ComfyUI"

echo "1/7: Installing System Dependencies..."
sudo apt update && sudo apt install -y python3-venv git build-essential

echo "2/7: creating Workspace & Virtual Environment..."
mkdir -p "$WORKSPACE_ROOT"
cd "$WORKSPACE_ROOT"

if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv "$VENV_PATH"
fi
source "$VENV_PATH/bin/activate"

echo "3/7: Installing PyTorch & Drivers..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo "4/7: Installing Requirements..."
# We go back to the repo config folder to find requirements.txt
if [ -f "$HOME/deadlygraphics/config_files/requirements.txt" ]; then
    pip install -r "$HOME/deadlygraphics/config_files/requirements.txt"
else
    echo "requirements.txt not found, skipping."
fi

echo "5/7: Cloning ComfyUI..."
if [ -d "$COMFY_PATH" ]; then
    echo "ComfyUI already exists. Skipping clone."
else
    git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFY_PATH"
fi

echo "6/7: Linking Models (C:\AI\models -> ComfyUI)..."
rm -rf "$COMFY_PATH/models"
ln -s /mnt/c/AI/models "$COMFY_PATH/models"

echo "7/7: Setup Complete."
echo "Launch with: cd $COMFY_PATH && python main.py --listen"
