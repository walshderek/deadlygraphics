#!/bin/bash
set -e

echo "💎 DIAMOND STACK PROVISIONING (LEGACY PATHS v3)..."

# --- 1. SETUP ENVIRONMENT & CACHE (Crucial for AI-Toolkit) ---
# This redirects the massive Hugging Face downloads to Windows
if ! grep -q "HF_HOME" ~/.bashrc; then
    echo '' >> ~/.bashrc
    echo '# Deadly Graphics Config' >> ~/.bashrc
    echo 'export HF_HOME="/mnt/c/AI/models/huggingface"' >> ~/.bashrc
    echo 'export WORKSPACE=~/workspace/deadlygraphics' >> ~/.bashrc
fi
# Export for this session immediately
export HF_HOME="/mnt/c/AI/models/huggingface"

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

# ComfyUI
if [ ! -d "ComfyUI" ]; then
    git clone https://github.com/comfyanonymous/ComfyUI.git
    cd ComfyUI
    python3 -m venv venv
    source venv/bin/activate
    pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu124
    pip install -r requirements.txt
    deactivate
    cd ..
fi

# AI-Toolkit
if [ ! -d "ai-toolkit" ]; then
    git clone https://github.com/ostris/ai-toolkit.git
    cd ai-toolkit
    python3 -m venv venv
    source venv/bin/activate
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
    pip install -r requirements.txt
    deactivate
    # Create the .env file for the token (User must fill this)
    if [ ! -f .env ]; then
        echo "HF_TOKEN=" > .env
    fi
    cd ..
fi

# OneTrainer
if [ ! -d "OneTrainer" ]; then
    git clone https://github.com/Nerogar/OneTrainer.git
    cd OneTrainer
    python3 -m venv venv
    source venv/bin/activate
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    pip install -r requirements.txt
    deactivate
    cd ..
fi

# --- 5. CONFIGURATION & LINKING ---
# Link the Windows Model Library
if [ ! -L "\/ai/models" ]; then
    ln -s /mnt/c/AI/models \/ai/models
fi

# GENERATE COMFYUI CONFIG (The Legacy Fix)
# We force ComfyUI to look in your OLD folders (Stable-diffusion)
COMFY_CONFIG="\/ai/apps/ComfyUI/extra_model_paths.yaml"
cat > "\" <<EOL
comfyui:
    base_path: /mnt/c/AI/models
    # Legacy Mappings (Matches your C:\AI\models structure)
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
