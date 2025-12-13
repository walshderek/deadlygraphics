# 1. Navigate to your repo
cd C:\Users\seanf\Documents\GitHub\deadlygraphics

# 2. Update the Linux Provisioning Script
@"
#!/bin/bash
set -e # Exit immediately if a command fails

echo "💎 DIAMOND STACK PROVISIONING STARTED..."

# --- 1. PREPARE WORKSPACE ---
export WORKSPACE=~/workspace/deadlygraphics
echo "Creating Workspace at \$WORKSPACE..."
mkdir -p \$WORKSPACE/ai/apps

# --- 2. CLONE MAIN REPO (DEADLY GRAPHICS) ---
# We clone this first to get your custom scripts (DG_*)
if [ ! -d "\$WORKSPACE/.git" ]; then
    echo "Cloning Deadly Graphics Repo..."
    # Cloning into temp and moving to avoid 'directory not empty' errors if created above
    git clone https://github.com/walshderek/deadlygraphics.git /tmp/dg_repo
    cp -r /tmp/dg_repo/* \$WORKSPACE/
    cp -r /tmp/dg_repo/.* \$WORKSPACE/ 2>/dev/null || true
    rm -rf /tmp/dg_repo
else
    echo "Deadly Graphics Repo already exists. Pulling latest..."
    cd \$WORKSPACE
    git pull
fi

# --- 3. INSTALL ENGINES (The 4 Pillars) ---
cd \$WORKSPACE/ai/apps

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

# B. AI-Toolkit (Flux/SDXL Training)
if [ ! -d "ai-toolkit" ]; then
    echo "Installing AI-Toolkit..."
    git clone https://github.com/ostris/ai-toolkit.git
    cd ai-toolkit
    python3 -m venv venv
    source venv/bin/activate
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
    pip install -r requirements.txt
    deactivate
    cd ..
fi

# C. OneTrainer (Deep Fine-Tuning)
if [ ! -d "OneTrainer" ]; then
    echo "Installing OneTrainer..."
    git clone https://github.com/Nerogar/OneTrainer.git
    cd OneTrainer
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    deactivate
    cd ..
fi

# D. Musubi Tuner (Wan 2.2 Video)
if [ ! -d "musubi-tuner" ]; then
    echo "Installing Musubi Tuner (Wan Branch)..."
    git clone -b wan https://github.com/kohya-ss/musubi-tuner.git
    cd musubi-tuner
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    deactivate
    cd ..
fi

# --- 4. THE "ONE TRUE PATH" CONFIG ---
echo "Linking Windows Model Library..."

# Link the global model folder
if [ ! -L "\$WORKSPACE/ai/models" ]; then
    ln -s /mnt/c/AI/models \$WORKSPACE/ai/models
fi

# Configure HuggingFace Cache Redirection (Saves Linux Drive Space)
if ! grep -q "HF_HOME" ~/.bashrc; then
    echo '' >> ~/.bashrc
    echo '# Deadly Graphics Config' >> ~/.bashrc
    echo 'export HF_HOME="/mnt/c/AI/models/huggingface"' >> ~/.bashrc
    echo 'export WORKSPACE=~/workspace/deadlygraphics' >> ~/.bashrc
fi

# Apply the ComfyUI YAML fix (Point to Windows drive)
COMFY_CONFIG="\$WORKSPACE/ai/apps/ComfyUI/extra_model_paths.yaml"
if [ ! -f "\$COMFY_CONFIG" ]; then
    echo "Creating ComfyUI Model Config..."
    cat > "\$COMFY_CONFIG" <<EOL
comfyui:
    base_path: /mnt/c/AI/models
    checkpoints: checkpoints
    clip: clip
    clip_vision: clip_vision
    configs: configs
    controlnet: controlnet
    embeddings: embeddings
    loras: loras
    upscale_models: upscale_models
    vae: vae
EOL
fi

echo "💎 DIAMOND STACK PROVISIONING COMPLETE."
"@ | Out-File -FilePath windows/provision_stack.sh -Encoding utf8

# 3. Commit and Push
git add windows/provision_stack.sh
git commit -m "Update: Added full Deadly Graphics stack installation to provision script"
git push origin main