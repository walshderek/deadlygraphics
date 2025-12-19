#!/bin/bash
# DeadlyMusubi Training Template
# Enhanced version of wan_train_template.sh with OOM/NaN mitigation

set -e  # Exit on error

# --- CONFIGURATION ---
PROJECT_NAME="${1:-my_project}"
TRIGGER_WORD="${2:-ohwx}"

# Paths
WSL_MODEL_ROOT="/mnt/c/AI/models"
WSL_APP_ROOT="/home/seanf/workspace/deadlygraphics/ai/apps/musubi-tuner"
OUTPUT_ROOT="/mnt/c/AI/outputs"

# --- MODEL PATHS (Wan 2.2 Standard) ---
DIT_LOW="${WSL_MODEL_ROOT}/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/fp16/wan2.2_t2v_low_noise_14B_fp16.safetensors"
DIT_HIGH="${WSL_MODEL_ROOT}/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/fp16/wan2.2_t2v_high_noise_14B_fp16.safetensors"
VAE="${WSL_MODEL_ROOT}/vae/WAN/wan_2.1_vae.pth"
T5="${WSL_MODEL_ROOT}/clip/models_t5_umt5-xxl-enc-bf16.pth"

# --- TRAINING PARAMETERS ---
# Memory optimization (adjust based on VRAM)
FP8_FLAGS="--fp8_base --fp8_scaled --fp8_t5"  # For 12-16GB VRAM
# Use "--bf16" instead for 24GB+ VRAM

# Optimizer (AdamW8bit for memory savings)
OPTIMIZER="AdamW8bit"
# Alternative: "AdamW" for full precision (requires more VRAM)

# Learning rate with warmup to prevent NaN
LEARNING_RATE="0.0001"
WARMUP_STEPS="100"
MAX_STEPS="5000"

# Batch and accumulation
BATCH_SIZE="1"
GRADIENT_ACCUMULATION="4"  # Effective batch size = 4

# Advanced options
GRADIENT_CHECKPOINTING="--gradient_checkpointing"  # Saves ~20% VRAM
MIXED_PRECISION="--mixed_precision fp16"

# --- DATASET CONFIG ---
DATASET_CONFIG="${WSL_APP_ROOT}/files/tomls/${PROJECT_NAME}.toml"

# --- OUTPUT ---
OUTPUT_DIR="${OUTPUT_ROOT}/${PROJECT_NAME}"
OUTPUT_NAME="${PROJECT_NAME}_${TRIGGER_WORD}"

# --- SAFETY CHECKS ---
echo "DeadlyMusubi Training Script"
echo "============================"
echo ""
echo "Configuration:"
echo "  Project: $PROJECT_NAME"
echo "  Trigger: $TRIGGER_WORD"
echo "  Output: $OUTPUT_DIR"
echo ""

# Check if dataset config exists
if [ ! -f "$DATASET_CONFIG" ]; then
    echo "ERROR: Dataset config not found: $DATASET_CONFIG"
    echo "Please create a TOML file for your dataset."
    exit 1
fi

# Check VRAM
if command -v nvidia-smi &> /dev/null; then
    vram_total=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n1)
    vram_free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -n1)
    
    echo "GPU Status:"
    echo "  Total VRAM: ${vram_total}MB"
    echo "  Free VRAM: ${vram_free}MB"
    echo ""
    
    if [ "$vram_free" -lt 10000 ]; then
        echo "WARNING: Low free VRAM. Close other GPU applications."
        echo "Continue? (y/n)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "Aborted."
            exit 0
        fi
    fi
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# --- MONITORING SETUP ---
# Log file for tracking
LOG_FILE="${OUTPUT_DIR}/training_log_$(date +%Y%m%d_%H%M%S).txt"

echo "Starting training..."
echo "Log file: $LOG_FILE"
echo ""

# --- TRAINING COMMAND ---
# Using accelerate for distributed training support
accelerate launch --num_processes 1 \
    "${WSL_APP_ROOT}/wan_train_network.py" \
    --dataset_config "$DATASET_CONFIG" \
    --dit "$DIT_LOW" \
    --dit_high_noise "$DIT_HIGH" \
    --t5 "$T5" \
    --vae "$VAE" \
    --output_dir "$OUTPUT_DIR" \
    --output_name "$OUTPUT_NAME" \
    $FP8_FLAGS \
    --optimizer_type "$OPTIMIZER" \
    --learning_rate "$LEARNING_RATE" \
    --warmup_steps "$WARMUP_STEPS" \
    --max_train_steps "$MAX_STEPS" \
    --train_batch_size "$BATCH_SIZE" \
    --gradient_accumulation_steps "$GRADIENT_ACCUMULATION" \
    $GRADIENT_CHECKPOINTING \
    $MIXED_PRECISION \
    --save_every_n_steps 500 \
    --sample_every_n_steps 500 \
    --logging_dir "$OUTPUT_DIR/logs" \
    --seed 42 \
    2>&1 | tee "$LOG_FILE"

# --- POST-TRAINING ---
echo ""
echo "Training complete!"
echo "Output saved to: $OUTPUT_DIR"
echo "Log file: $LOG_FILE"

# Check for common issues in log
if grep -q "CUDA out of memory" "$LOG_FILE"; then
    echo ""
    echo "WARNING: OOM detected in logs!"
    echo "Suggestions:"
    echo "  - Reduce batch size or gradient accumulation"
    echo "  - Enable more aggressive fp8 settings"
    echo "  - Reduce resolution or sequence length"
fi

if grep -q "NaN" "$LOG_FILE" || grep -q "nan" "$LOG_FILE"; then
    echo ""
    echo "WARNING: NaN detected in logs!"
    echo "Suggestions:"
    echo "  - Reduce learning rate"
    echo "  - Increase warmup steps"
    echo "  - Check dataset for corrupted samples"
    echo "  - Try different optimizer (e.g., SGD)"
fi
