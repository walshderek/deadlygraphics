# WAN 2.2 TRAINING TEMPLATE (Linux/WSL)
# Usage: ./train_wan.sh [PROJECT_NAME]
# Note: Paths converted from C:\AI to /mnt/c/AI

# --- CONFIG ---
PROJECT_NAME="\"
TRIGGER_WORD="ohwx" # Default trigger, can be overridden
WSL_MODEL_ROOT="/mnt/c/AI/models"
WSL_APP_ROOT="/home/seanf/workspace/deadlygraphics/ai/apps/musubi-tuner"

# --- MODEL PATHS (Wan 2.2 Standard) ---
# Note: Wan 2.2 paths confirmed from original batch file
DIT_LOW="\/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/fp16/wan2.2_t2v_low_noise_14B_fp16.safetensors"
DIT_HIGH="\/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/fp16/wan2.2_t2v_high_noise_14B_fp16.safetensors"
VAE="\/vae/WAN/wan_2.1_vae.pth"
T5="\/clip/models_t5_umt5-xxl-enc-bf16.pth"

# --- COMMAND ---
accelerate launch --num_processes 1 "wan_train_network.py" \
  --dataset_config "\/files/tomls/\.toml" \
  --dit "\" \
  --dit_high_noise "\" \
  --t5 "\" \
  --vae "\" \
  --output_dir "\/outputs/\" \
  --output_name "\" \
  --fp8_base --fp8_scaled --fp8_t5 \
  --optimizer_type AdamW8bit \
  --learning_rate 0.0001
