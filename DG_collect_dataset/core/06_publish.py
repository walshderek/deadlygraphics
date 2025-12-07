import sys
import os
import utils
import shutil
from pathlib import Path

# --- TEMPLATE GENERATORS ---

def generate_toml(slug, img_dir_path, os_type, resolution):
    if os_type == "win":
        clean_path = img_dir_path.replace("\\", "\\\\")
    else:
        clean_path = img_dir_path
    
    res_str = f"[{resolution},{resolution}]"
    
    toml_content = f"""[general]
caption_extension = ".txt"
batch_size = 1
enable_bucket = true
bucket_no_upscale = false

[[datasets]]
image_directory = "{clean_path}"
cache_directory = "{clean_path}_cache"
num_repeats = 1
resolution = {res_str}
"""
    return toml_content

def generate_bat(slug, toml_path_win_c, toml_path_win_unc):
    # Uses MUSUBI_PATHS from utils
    return f"""@echo off
SETLOCAL enabledelayedexpansion

REM --- SET BASE PATHS ---
set "WAN_ROOT={utils.MUSUBI_PATHS['win_app']}"
set "C_MODEL_BASE={utils.MUSUBI_PATHS['win_models']}"

REM --- CONFIG AND OUTPUT PATHS ---
set "CFG={toml_path_win_c}"
set "OUT=%WAN_ROOT%\\outputs\\{slug}"
set "LOGDIR=%WAN_ROOT%\\logs"
set "OUTNAME={slug}"

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
echo Starting VAE Latent Cache Generation...
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
echo Starting LoRA Training...
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

def generate_sh(slug, toml_path_wsl):
    return f"""#!/bin/bash
set -x

# --- PATHS ---
MODELS_ROOT="{utils.MUSUBI_PATHS['wsl_models']}"
WAN_DIR="{utils.MUSUBI_PATHS['wsl_app']}"
CFG="{toml_path_wsl}"

DIT_LOW="${{MODELS_ROOT}}/diffusion-models/Wan/Wan2.2/14B/Wan_2_2_T2V/fp16/wan2.2_t2v_low_noise_14B_fp16.safetensors"
DIT_HIGH="${{MODELS_ROOT}}/diffusion-models/Wan/Wan2.2/14B/Wan_2_2_T2V/fp16/wan2.2_t2v_high_noise_14B_fp16.safetensors"
VAE="${{MODELS_ROOT}}/vae/wan_2.1_vae.pth"
T5="${{MODELS_ROOT}}/clip/models_t5_umt5-xxl-enc-bf16.pth"

OUT="${{WAN_DIR}}/outputs/{slug}"
OUTNAME="{slug}"
LOGDIR="${{WAN_DIR}}/logs"

# --- EXECUTION ---
cd "${{WAN_DIR}}/"
source venv/bin/activate

echo "### Caching VAE latents... ###"
python wan_cache_latents.py \\
  --dataset_config "${{CFG}}" \\
  --vae "${{VAE}}" \\
  --vae_dtype float16 \\
  --vae_cache_cpu

echo "### Caching T5 text encoder outputs... ###"
python wan_cache_text_encoder_outputs.py \\
  --dataset_config "${{CFG}}" \\
  --t5 "${{T5}}" \\
  --batch_size 16 \\
  --fp8_t5

echo "### Starting training... ###"
accelerate launch --num_processes 1 "wan_train_network.py" \\
  --dataset_config "${{CFG}}" \\
  --discrete_flow_shift 3 \\
  --dit "${{DIT_LOW}}" \\
  --dit_high_noise "${{DIT_HIGH}}" \\
  --fp8_base \\
  --fp8_scaled \\
  --fp8_t5 \\
  --gradient_accumulation_steps 1 \\
  --gradient_checkpointing \\
  --img_in_txt_in_offloading \\
  --learning_rate 0.0001 \\
  --log_with tensorboard \\
  --logging_dir "${{LOGDIR}}" \\
  --lr_scheduler cosine \\
  --lr_warmup_steps 100 \\
  --max_data_loader_n_workers 6 \\
  --max_timestep 1000 \\
  --max_train_epochs 35 \\
  --min_timestep 0 \\
  --mixed_precision fp16 \\
  --network_alpha 8 \\
  --network_args "verbose=True" "exclude_patterns=[]" \\
  --network_dim 8 \\
  --network_module networks.lora_wan \\
  --offload_inactive_dit \\
  --optimizer_type AdamW8bit \\
  --output_dir "${{OUT}}" \\
  --output_name "${{OUTNAME}}" \\
  --persistent_data_loader_workers \\
  --max_train_steps 1400 \\
  --save_every_n_epochs 5 \\
  --seed 42 \\
  --t5 "${{T5}}" \\
  --task t2v-A14B \\
  --timestep_boundary 875 \\
  --timestep_sampling logsnr \\
  --vae "${{VAE}}" \\
  --vae_cache_cpu \\
  --vae_dtype float16 \\
  --sdpa

echo "Done."
"""

# --- MAIN EXECUTION ---
def run(project_slug):
    slug = project_slug
    
    # --- FIXED RESOLUTION ---
    TARGET_RES = 256
    res_str = str(TARGET_RES)
    
    # --- FILE NAMES ---
    toml_wsl_name = f"{slug}_{res_str}_wsl.toml"
    sh_wsl_name = f"train_{slug}_{res_str}_wsl.sh"
    toml_win_name = f"{slug}_{res_str}_win.toml"
    bat_win_name = f"train_{slug}_{res_str}_win.bat"
    
    path = utils.get_project_path(slug)
    
    # Source Image Path (WSL)
    wsl_img_path = path / utils.DIRS['downsample'] / res_str 
    
    if not wsl_img_path.exists():
        print(f"❌ Downsample directory missing at {wsl_img_path}. Run Step 5 first.")
        return

    # --- DESTINATIONS ---
    # Windows Write Target (via /mnt/c)
    # Mapping C:\AI\apps... to /mnt/c/AI/apps...
    win_mount_root = Path("/mnt/c/AI/apps/musubi-tuner") 
    
    # Subdirs
    win_toml_dir = win_mount_root / "files" / "tomls"
    win_bat_dir = win_mount_root
    
    win_toml_dir.mkdir(parents=True, exist_ok=True)
    
    # --- UNC PATHS FOR CONFIG CONTENT ---
    win_unc_img_path = utils.get_windows_unc_path(str(wsl_img_path))
    
    # --- GENERATE & WRITE ---
    print(f"🚀 Deploying {TARGET_RES}x{TARGET_RES} configs for '{slug}'...")

    # 1. WSL Files (Written to local app folder or /mnt/c if user prefers? 
    # Original pasted code wrote WSL files to local `wsl_musubi_root`. 
    # I will write them to the Project Output folder for safekeeping/execution)
    
    local_output_dir = path / "06_publish"
    local_output_dir.mkdir(parents=True, exist_ok=True)
    
    toml_wsl_content = generate_toml(slug, str(wsl_img_path), "wsl", TARGET_RES)
    sh_wsl_content = generate_sh(slug, str(local_output_dir / toml_wsl_name))
    
    with open(local_output_dir / toml_wsl_name, "w") as f: f.write(toml_wsl_content)
    with open(local_output_dir / sh_wsl_name, "w") as f: f.write(sh_wsl_content)
    os.chmod(local_output_dir / sh_wsl_name, 0o755)

    # 2. WINDOWS Files (Written to /mnt/c/AI/apps/musubi-tuner)
    
    # Path inside the BAT file needs to point to C:\...
    win_toml_c_path = f"{utils.MUSUBI_PATHS['win_app']}\\files\\tomls\\{toml_win_name}"
    
    toml_win_content = generate_toml(slug, win_unc_img_path, "win", TARGET_RES)
    bat_win_content = generate_bat(slug, win_toml_c_path, win_toml_c_path)
    
    # Write TOML to /mnt/c/.../files/tomls/
    with open(win_toml_dir / toml_win_name, "w") as f: f.write(toml_win_content)
    
    # Write BAT to /mnt/c/.../
    with open(win_bat_dir / bat_win_name, "w") as f: f.write(bat_win_content)

    print("\n✅ Deployment Complete:")
    print(f"   📂 WSL Files (Local): {local_output_dir}")
    print(f"   🪟 Windows TOML: {win_toml_dir / toml_win_name}")
    print(f"   🪟 Windows BAT:  {win_bat_dir / bat_win_name}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])