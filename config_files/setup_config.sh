#!/bin/bash
set -e

echo "1/7: Installing System Dependencies..."
sudo apt update && sudo apt install -y python3-venv git build-essential

echo "2/7: creating Virtual Environment (ai_env)..."
python3 -m venv ai_env
source ai_env/bin/activate

echo "3/7: Installing PyTorch & Drivers..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo "4/7: Installing Requirements..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "requirements.txt not found, skipping."
fi

echo "5/7: Cloning ComfyUI..."
if [ -d "ComfyUI" ]; then
    echo "ComfyUI already exists. Skipping clone."
else
    git clone https://github.com/comfyanonymous/ComfyUI.git
fi

echo "6/7: Linking Models (C:\AI\models -> ComfyUI)..."
rm -rf ComfyUI/models
ln -s /mnt/c/AI/models ComfyUI/models

echo "7/7: Setup Complete."
echo "Launch with: cd ComfyUI && python main.py --listen"
