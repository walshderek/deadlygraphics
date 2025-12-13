#!/bin/bash
set -e

# =================================================
# 💎 DIAMOND SMASHING MACHINE — APP PROVISIONING 💎
# =================================================

PYTHON_VER="3.12"
WORKSPACE_ROOT="$HOME/workspace/deadlygraphics/ai/apps"

TORCH_CUDA_INDEX="https://download.pytorch.org/whl/cu124"

declare -A REPOS=(
    ["DG_vibecoder"]="https://github.com/deadlygraphics/DG_vibecoder.git"
    ["ComfyUI"]="https://github.com/comfyanonymous/ComfyUI.git"
    ["OneTrainer"]="https://github.com/Nerogar/OneTrainer.git"
    ["ai-toolkit"]="https://github.com/ostris/ai-toolkit.git"
    ["musubi-tuner"]="https://github.com/sdbds/musubi-tuner-scripts.git"
    ["video-scraper"]="https://github.com/deadlygraphics/video-scraper.git"
    ["DG_collect_dataset"]="https://github.com/deadlygraphics/dg_collect_dataset.git"
)

echo "================================================="
echo "💎 PROVISIONING APPS & VIRTUAL ENVIRONMENTS 💎"
echo "================================================="

# ---------- SYSTEM CHECKS ----------
echo "🔍 Verifying Python $PYTHON_VER..."
python$PYTHON_VER --version

echo "🔍 Verifying NVIDIA GPU visibility..."
nvidia-smi >/dev/null

# ---------- CLONE REPOS ----------
echo "📁 Ensuring workspace layout..."
mkdir -p "$WORKSPACE_ROOT"
cd "$WORKSPACE_ROOT"

for app in "${!REPOS[@]}"; do
    if [ ! -d "$app" ]; then
        echo "⬇️ Cloning $app"
        git clone "${REPOS[$app]}" "$app"
    else
        echo "✅ $app exists"
    fi
done

# ---------- VENV SETUP ----------
setup_venv() {
    local app_dir="$1"
    local install_torch="$2"

    echo "🛠️ Setting up venv for $(basename "$app_dir")"
    cd "$app_dir"

    if [ ! -d ".venv" ]; then
        python$PYTHON_VER -m venv .venv
    fi

    source .venv/bin/activate
    pip install --upgrade pip wheel

    if [ "$install_torch" = "yes" ]; then
        echo "🔥 Installing CUDA Torch"
        pip install torch torchvision torchaudio --index-url "$TORCH_CUDA_INDEX"

        echo "🧪 Verifying CUDA availability"
        python - <<'EOF'
import torch, sys
print("Torch:", torch.__version__)
print("CUDA:", torch.version.cuda)
print("CUDA available:", torch.cuda.is_available())
if not torch.cuda.is_available():
    print("❌ CUDA NOT AVAILABLE — ABORTING")
    sys.exit(1)
EOF
    fi

    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi

    deactivate
    cd "$WORKSPACE_ROOT"
}

# ---------- GPU APPS ----------
setup_venv "$WORKSPACE_ROOT/ComfyUI" yes
setup_venv "$WORKSPACE_ROOT/OneTrainer" yes
setup_venv "$WORKSPACE_ROOT/ai-toolkit" yes
setup_venv "$WORKSPACE_ROOT/musubi-tuner" yes

# ---------- CPU / MIXED ----------
setup_venv "$WORKSPACE_ROOT/DG_vibecoder" no
setup_venv "$WORKSPACE_ROOT/video-scraper" no
setup_venv "$WORKSPACE_ROOT/DG_collect_dataset" yes

echo "================================================="
echo "💎 ALL VENV SETUP COMPLETE — GPU VERIFIED 💎"
echo "================================================="
