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

DIT_LOW="${{MODELS_ROOT}}/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/fp16/wan2.2_t2v_low_noise_14B_fp16.safetensors"
DIT_HIGH="${{MODELS_ROOT}}/diffusion_models/Wan/Wan2.2/14B/Wan_2_2_T2V/fp16/wan2.2_t2v_high_noise_14B_fp16.safetensors"
VAE="${{MODELS_ROOT}}/vae/wan_2.1_vae.safetensors"
T5="${{MODELS_ROOT}}/text_encoders/umt5-xxl-enc-bf16.safetensors"

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
    
    # --- FIXED RESOLUTION CONFIGURATION ---
    TARGET_RES = 256
    res_str = str(TARGET_RES)
    
    # --- FILE NAME DEFINITIONS ---
    toml_wsl_name = f"{slug}_{res_str}_wsl.toml"
    sh_wsl_name = f"train_{slug}_{res_str}_wsl.sh"
    toml_win_name = f"{slug}_{res_str}_win.toml"
    bat_win_name = f"train_{slug}_{res_str}_win.bat"
    
    path = utils.get_project_path(slug)
    
    # Source Image Path
    wsl_img_path = path / utils.DIRS['publish'] / res_str
    
    if not wsl_img_path.exists():
        print(f"❌ Publish directory missing at {wsl_img_path}. Run Step 5 first.")
        return

    # --- SETUP TARGET DIRECTORIES ---
    
    # WSL Targets
    wsl_musubi_root = Path(utils.MUSUBI_PATHS['wsl_app'])
    wsl_toml_target = wsl_musubi_root / "TOML" 
    wsl_bat_target = wsl_musubi_root / "BAT"
    
    # Create them locally in WSL
    wsl_toml_target.mkdir(parents=True, exist_ok=True)
    wsl_bat_target.mkdir(parents=True, exist_ok=True)
    
    # Windows UNC Targets
    win_toml_target_unc = utils.get_windows_unc_path(str(wsl_toml_target))
    win_bat_target_unc = utils.get_windows_unc_path(str(wsl_bat_target))
    win_unc_img_path = utils.get_windows_unc_path(str(wsl_img_path))
    
    # Native Windows C: Targets
    # Note: We rely on WSL writing to the mounted paths, but the content inside the scripts
    # must point to C:\AI\apps\musubi-tuner\TOML etc.
    
    # --- 4. GENERATE & DEPLOY ---
    print(f"🚀 Deploying {TARGET_RES}x{TARGET_RES} configs for '{slug}'...")

    # --- A. WSL Files ---
    toml_wsl_content = generate_toml(slug, str(wsl_img_path), "wsl", TARGET_RES)
    sh_wsl_content = generate_sh(slug, str(wsl_toml_target / toml_wsl_name))
    
    with open(wsl_toml_target / toml_wsl_name, "w") as f: f.write(toml_wsl_content)
    with open(wsl_bat_target / sh_wsl_name, "w") as f: f.write(sh_wsl_content)
    os.chmod(wsl_bat_target / sh_wsl_name, 0o755)
    
    # --- B. WINDOWS Files ---
    
    # Paths inside the BAT file need to point to C:\...
    # We construct the C: path for the TOML file
    win_toml_c_path = f"{utils.MUSUBI_PATHS['win_app']}\\TOML\\{toml_win_name}"
    
    toml_win_content = generate_toml(slug, win_unc_img_path, "win", TARGET_RES)
    bat_win_content = generate_bat(slug, win_toml_c_path, win_toml_c_path)
    
    # Write using UNC paths
    win_toml_dest = Path(f"{win_toml_target_unc}\\{toml_win_name}".replace("/", "\\"))
    win_bat_dest = Path(f"{win_bat_target_unc}\\{bat_win_name}".replace("/", "\\"))
    
    with open(win_toml_dest, "w") as f: f.write(toml_win_content)
    with open(win_bat_dest, "w") as f: f.write(bat_win_content)

    print("\n✅ Deployment Complete:")
    print(f"   📂 TOML Folder: {wsl_toml_target}")
    print(f"   📂 BAT Folder:  {wsl_bat_target}")
    print(f"   🪟 Created: {toml_win_name}")
    print(f"   🪟 Created: {bat_win_name}")
    print("\n👉 Database updated and files organized.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])
    else:
        print("Usage: python 06_publish.py <slug>")