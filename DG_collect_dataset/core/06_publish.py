"""
Script Name: 06_publish.py
Author: DeadlyGraphics
Date: 2025-12-06
"""

import os
from pathlib import Path

# --- CONFIGURATION ---
RESOLUTIONS = [256, 512, 1024]

# DESTINATIONS: STRICTLY /mnt/c/AI/apps/musubi-tuner/
DEST_TOML_DIR = Path('/mnt/c/AI/apps/musubi-tuner/files/tomls/')
DEST_BAT_DIR = Path('/mnt/c/AI/apps/musubi-tuner/')

def get_toml_content(image_dir_win, cache_dir_win, resolution):
    return f"""[general]
caption_extension = ".txt"
batch_size = 1
enable_bucket = true
bucket_no_upscale = false

[[datasets]]
image_directory = "{image_dir_win}"
cache_directory = "{cache_dir_win}"
num_repeats = 1
resolution = [{resolution},{resolution}]
"""

def get_bat_content(slug, resolution, toml_filename):
    win_cfg_path = f"C:\\AI\\apps\\musubi-tuner\\files\\tomls\\{toml_filename}"
    
    return f"""@echo off
SETLOCAL enabledelayedexpansion

REM --- SET BASE PATHS ---
set "WAN_ROOT=C:\\AI\\apps\\musubi-tuner"
set "C_MODEL_BASE=\\\\wsl.localhost\\Ubuntu\\home\\seanf\\ai\\models"

REM --- CONFIG AND OUTPUT PATHS ---
set "CFG={win_cfg_path}"
set "OUT=%WAN_ROOT%\\outputs\\{slug}"
set "LOGDIR=%WAN_ROOT%\\logs"
set "OUTNAME={slug}_{resolution}"

REM --- MODEL PATHS ---
set "DIT_LOW=%C_MODEL_BASE%\\diffusion-models\\Wan\\Wan2.2\\14B\\Wan_2_2_I2V\\fp16\\wan2.2_t2v_low_noise_14B_fp16.safetensors"
set "DIT_HIGH=%C_MODEL_BASE%\\diffusion-models\\Wan\\Wan2.2\\14B\\Wan_2_2_I2V\\fp16\\wan2.2_t2v_high_noise_14B_fp16.safetensors"
set "VAE=%C_MODEL_BASE%\\vae\\wan_2.1_vae.pth"
set "T5=%C_MODEL_BASE%\\clip\\models_t5_umt5-xxl-enc-bf16.pth"

REM --- ACTIVATE VENV ---
cd /d "%WAN_ROOT%"
call venv\\scripts\\activate

REM --- CREATE DIRS ---
if not exist "%OUT%" mkdir "%OUT%"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM 1. CACHE VAE LATENTS
echo Starting VAE Latent Cache Generation for {resolution}px...
python wan_cache_latents.py ^
  --dataset_config "%CFG%" ^
  --vae "%VAE%" ^
  --vae_dtype float16

REM 2. CACHE T5 EMBEDDINGS
echo Starting T5 Text Encoder Cache Generation...
python wan_cache_text_encoder_outputs.py ^
  --dataset_config "%CFG%" ^
  --t5 "%T5%" ^
  --batch_size 16 ^
  --fp8_t5

REM 3. TRAIN
echo Starting LoRA Training for {slug} @ {resolution}px...
accelerate launch --num_processes 1 "wan_train_network.py" ^
  --dataset_config "%CFG%" ^
  --discrete_flow_shift 3 ^
  --dit "%DIT_LOW%" ^
  --dit_high_noise "%DIT_HIGH%" ^
  --fp8_base ^
  --fp8_scaled ^
  --fp8_t5 ^
  --gradient_accumulation_steps 1 ^
  --gradient_checkpointing ^
  --img_in_txt_in_offloading ^
  --learning_rate 0.0001 ^
  --log_with tensorboard ^
  --logging_dir "%LOGDIR%" ^
  --lr_scheduler cosine ^
  --lr_warmup_steps 100 ^
  --max_data_loader_n_workers 6 ^
  --max_train_epochs 35 ^
  --max_timestep 1000 ^
  --min_timestep 0 ^
  --mixed_precision fp16 ^
  --network_alpha 8 ^
  --network_args "verbose=True" "exclude_patterns=[]" ^
  --network_dim 8 ^
  --network_module networks.lora_wan ^
  --offload_inactive_dit ^
  --optimizer_type AdamW8bit ^
  --output_dir "%OUT%" ^
  --output_name "%OUTNAME%" ^
  --save_every_n_epochs 5 ^
  --seed 42 ^
  --t5 "%T5%" ^
  --task t2v-A14B ^
  --timestep_boundary 875 ^
  --timestep_sampling logsnr ^
  --vae "%VAE%" ^
  --vae_cache_cpu ^
  --vae_dtype float16 ^
  --sdpa

pause
ENDLOCAL
"""

def convert_wsl_path_to_windows_network(linux_path):
    abs_path = str(linux_path.resolve())
    if not abs_path.startswith("/home"): return abs_path
    win_style = abs_path.replace("/", "\\")
    return f"\\\\\\\\wsl.localhost\\\\Ubuntu{win_style}"

def run(slug, trigger, model):
    print(f"=== 06 PUBLISH: Generating Configs for {slug} ===")
    
    base_dir = Path.cwd()
    # READS FROM: outputs/slug/05_downsample
    downsample_base = base_dir / "outputs" / slug / "05_downsample"
    
    if not downsample_base.exists():
        print(f"❌ Error: Downsample directory not found at {downsample_base}")
        return

    # Ensure destination directories exist
    DEST_TOML_DIR.mkdir(parents=True, exist_ok=True)
    DEST_BAT_DIR.mkdir(parents=True, exist_ok=True)
    
    for res in RESOLUTIONS:
        src_img_dir = downsample_base / str(res)
        src_cache_dir = downsample_base / f"{res}_cache" 
        
        if not src_img_dir.exists():
            print(f"⚠️  Skipping {res}px: Directory not found.")
            continue
            
        win_img_path = convert_wsl_path_to_windows_network(src_img_dir)
        win_cache_path = convert_wsl_path_to_windows_network(src_cache_dir)
        
        # TOML
        toml_filename = f"{slug}_{res}_win.toml"
        toml_content = get_toml_content(win_img_path, win_cache_path, res)
        dest_toml_path = DEST_TOML_DIR / toml_filename
        
        try:
            with open(dest_toml_path, 'w', encoding='utf-8') as f:
                f.write(toml_content)
            print(f"✅ [{res}px] TOML saved: {dest_toml_path}")
        except Exception as e:
            print(f"❌ [{res}px] Failed to save TOML: {e}")

        # BAT
        bat_filename = f"train_{slug}_{res}_win.bat"
        bat_content = get_bat_content(slug, res, toml_filename)
        dest_bat_path = DEST_BAT_DIR / bat_filename
        
        try:
            with open(dest_bat_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)
            print(f"✅ [{res}px] BAT saved:  {dest_bat_path}")
        except Exception as e:
            print(f"❌ [{res}px] Failed to save BAT: {e}")

    print(f"\n🎉 Publish Complete.")

if __name__ == "__main__":
    run("ed_milliband", "ohwx", "wan2.1")