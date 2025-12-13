#!/bin/bash
set -e

echo "💎 DIAMOND STACK PROVISIONING (BLOBS & SHARDS EDITION)..."

# --- 1. SETUP ENVIRONMENT & CACHE ---
# We point HF_HOME to 'blobs_shards' so all raw downloads go to Windows
# This prevents Linux drive bloat and allows apps to share downloaded weights
export CACHE_DIR="/mnt/c/AI/models/blobs_shards"
mkdir -p "\"

if ! grep -q "HF_HOME" ~/.bashrc; then
    echo '' >> ~/.bashrc
    echo '# Deadly Graphics Config' >> ~/.bashrc
    echo "export HF_HOME=\"\\"" >> ~/.bashrc
    echo 'export WORKSPACE=~/workspace/deadlygraphics' >> ~/.bashrc
fi
export HF_HOME="\"

# --- 2. PREPARE WORKSPACE ---
export WORKSPACE=~/workspace/deadlygraphics
mkdir -p \/ai/apps

# --- 3. CLONE REPO ---
if [ ! -d "\/.git" ]; then
    git clone https://github.com/walshderek/deadlygraphics.git /tmp/dg_repo
    cp -r /tmp/dg_repo/* \/
    rm -rf /tmp/dg_repo
else
    cd \ && git pull
fi

# --- 4. INSTALL APPS ---
cd \/ai/apps

# A. ComfyUI
if [ ! -d "ComfyUI" ]; then
    echo "Installing ComfyUI..."
    git clone https://github.com/comfyanonymous/ComfyUI.git
    cd ComfyUI
    python3 -m venv venv
    source venv/bin/activate
    pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu124
    pip install -r requirements.txt
    deactivate
    cd ..
fi

# B. AI-Toolkit
if [ ! -d "ai-toolkit" ]; then
    echo "Installing AI-Toolkit..."
    git clone https://github.com/ostris/ai-toolkit.git
    cd ai-toolkit
    python3 -m venv venv
    source venv/bin/activate
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
    pip install -r requirements.txt
    deactivate
    # Create the .env file for the token
    if [ ! -f .env ]; then
        echo "HF_TOKEN=" > .env
    fi
    cd ..
fi

# C. OneTrainer
if [ ! -d "OneTrainer" ]; then
    echo "Installing OneTrainer..."
    git clone https://github.com/Nerogar/OneTrainer.git
    cd OneTrainer
    python3 -m venv venv
    source venv/bin/activate
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    pip install -r requirements.txt
    deactivate
    cd ..
fi

# D. Musubi Tuner (Wan 2.2 Golden Commit)
if [ ! -d "musubi-tuner" ]; then
    echo "Installing Musubi Tuner (Wan 2.2 Fixed)..."
    git clone https://github.com/kohya-ss/musubi-tuner.git
    cd musubi-tuner
    # Checkout the golden commit for Wan 2.2 stability
    git checkout e7adb86
    
    python3 -m venv venv
    source venv/bin/activate
    pip install -e .
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
    deactivate
    cd ..
fi

# --- 5. CONFIGURATION & LINKING ---
# Link the Windows Model Library
if [ ! -L "\/ai/models" ]; then
    ln -s /mnt/c/AI/models \/ai/models
fi

# GENERATE COMFYUI CONFIG (Legacy Folder Fix)
COMFY_CONFIG="\/ai/apps/ComfyUI/extra_model_paths.yaml"
cat > "\" <<EOL
comfyui:
    base_path: /mnt/c/AI/models
    # Legacy Mappings (Matches C:\AI\models structure)
    checkpoints: Stable-diffusion
    unet: diffusion_models
    vae: vae
    clip: clip
    text_encoders: text_encoders
    loras: loras
    embeddings: embeddings
    controlnet: controlnet
    upscale_models: upscale_models
    diffusers: diffusers
    gligen: gligen
EOL

echo "💎 DIAMOND STACK PROVISIONING COMPLETE."
