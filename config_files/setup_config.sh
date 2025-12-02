#!/bin/bash
# V001 Setup Script for WSL AI Workstation (RTX 4080)

# --- 1. System Setup ---
echo "1/8: Installing dependencies and fixing paths..."
sudo apt update
sudo apt install build-essential procps curl file git -y
sudo apt install python3.12-venv -y

# --- 2. Homebrew/Git-Xet Setup ---
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc
source ~/.bashrc
brew install git-xet

# --- 3. CUDA Path Fix ---
echo "3/8: Fixing CUDA Path..."
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# --- 4. Python Environment Setup ---
echo "4/8: Setting up Python Virtual Environment..."
cd /workspaces/apps/ || mkdir -p /workspaces/apps/ && cd /workspaces/apps/
python3 -m venv ai_env
source ai_env/bin/activate

# --- 5. Install PyTorch & Python Dependencies ---
echo "5/8: Installing PyTorch and requirements..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r /home/${USER}/deadlygraphics/config_files/requirements.txt

# --- 6. Clone Application ---
echo "6/8: Cloning ComfyUI..."
git clone https://github.com/comfyanonymous/ComfyUI.git

# --- 7. Model Symlink ---
echo "7/8: Creating Model Symlink..."
cd ComfyUI/models/
rm -rf checkpoints # Remove empty placeholder
ln -s /mnt/c/AI/ComfyUI\ Desktop/models/ checkpoints
cd ../..

# --- 8. Complete ---
echo "8/8: Finalizing script."
chmod +x /home/${USER}/deadlygraphics/config_files/setup_config.sh

echo "✅ SETUP COMPLETE. RUN 'source /workspaces/apps/ai_env/bin/activate' in the next terminal session."
