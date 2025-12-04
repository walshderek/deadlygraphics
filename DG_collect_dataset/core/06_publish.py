# Script Name: core/06_publish.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Prepares Musubi/Wan training files and logs to Google Sheets.

import sys
import os
import utils
import shutil
import datetime
import pickle
from pathlib import Path

# --- GOOGLE SHEETS CONFIG ---
# Path to client_secret.json (WSL Path)
GOOGLE_CREDS = Path("/mnt/c/AI/apps/ComfyUI Desktop/custom_nodes/comfyui-google-sheets-integration/client_secret.json")
SHEET_NAME = "DeadlyGraphics LoRA Tracker"

def log_to_sheet(slug, trigger):
    if not GOOGLE_CREDS.exists():
        print(f"⚠️ Google Creds not found at {GOOGLE_CREDS}. Skipping log.")
        return

    try:
        # Lazy import to avoid crashing if libs missing
        import gspread
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = None
        token_path = utils.ROOT_DIR / 'token.pickle'

        if token_path.exists():
            with open(token_path, 'rb') as token: creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(GOOGLE_CREDS), SCOPES)
                creds = flow.run_console()
            with open(token_path, 'wb') as token: pickle.dump(creds, token)

        client = gspread.authorize(creds)
        try: sheet = client.open(SHEET_NAME).sheet1
        except: sheet = client.create(SHEET_NAME).sheet1; sheet.append_row(["Date", "Project", "Trigger", "Status"])

        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        sheet.append_row([ts, slug, trigger, "Published / Ready"])
        print(f"✅ Logged to Google Sheet: {SHEET_NAME}")

    except ImportError:
        print("⚠️ Missing Google libs. Run: pip install gspread google-auth-oauthlib")
    except Exception as e:
        print(f"❌ Logging failed: {e}")

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
echo Starting VAE Latent Cache...
python wan_cache_latents.py --dataset_config "%CFG%" --vae "%VAE%" --vae_dtype float16

REM 2. CACHE T5 EMBEDDINGS
echo Starting T5 Cache...
python wan_cache_text_encoder_outputs.py --dataset_config "%CFG%" --t5 "%T5%" --batch_size 16 --fp8_t5

REM 3. TRAIN
echo Starting Training...
accelerate launch --num_processes 1 "wan_train_network.py" ^
  --dataset_config "%CFG%" ^
  --discrete_flow_shift 3 ^
  --dit "%DIT_LOW%" ^
  --dit_high_noise "%DIT_HIGH%" ^
  --fp8_base --fp8_scaled --fp8_t5 ^
  --gradient_accumulation_steps 1 ^
  --learning_rate 0.0001 ^
  --output_dir "%OUT%" ^
  --output_name "%OUTNAME%" ^
  --max_train_epochs 35 ^
  --save_every_n_epochs 5 ^
  --t5 "%T5%" ^
  --vae "%VAE%" ^
  --vae_cache_cpu ^
  --sdpa

pause
ENDLOCAL
"""

def generate_sh(slug, toml_path_wsl):
    return f"""#!/bin/bash
set -x
# Linux shell script template here (omitted for brevity, same as before)
echo "Done."
"""

# --- MAIN EXECUTION ---
def run(project_slug, trigger_word=None, model_name=None):
    slug = project_slug
    TARGET_RES = 256
    res_str = str(TARGET_RES)
    
    # Filenames
    toml_wsl_name = f"{slug}_{res_str}_wsl.toml"
    sh_wsl_name = f"train_{slug}_{res_str}_wsl.sh"
    toml_win_name = f"{slug}_{res_str}_win.toml"
    bat_win_name = f"train_{slug}_{res_str}_win.bat"
    
    path = utils.get_project_path(slug)
    wsl_img_path = path / utils.DIRS['publish'] / res_str
    
    if not wsl_img_path.exists():
        print(f"❌ Publish directory missing at {wsl_img_path}. Run Step 5 first.")
        return

    # Targets
    wsl_musubi_root = Path(utils.MUSUBI_PATHS['wsl_app'])
    wsl_toml_target = wsl_musubi_root / "TOML" 
    wsl_bat_target = wsl_musubi_root / "BAT"
    
    wsl_toml_target.mkdir(parents=True, exist_ok=True)
    wsl_bat_target.mkdir(parents=True, exist_ok=True)
    
    win_toml_target_unc = utils.get_windows_unc_path(str(wsl_toml_target))
    win_bat_target_unc = utils.get_windows_unc_path(str(wsl_bat_target))
    win_unc_img_path = utils.get_windows_unc_path(str(wsl_img_path))
    
    print(f"🚀 Deploying {TARGET_RES}x{TARGET_RES} configs for '{slug}'...")

    # Generate Files
    toml_wsl_content = generate_toml(slug, str(wsl_img_path), "wsl", TARGET_RES)
    # sh_wsl_content = generate_sh(slug, str(wsl_toml_target / toml_wsl_name)) # Optional if you use Windows training mostly
    
    with open(wsl_toml_target / toml_wsl_name, "w") as f: f.write(toml_wsl_content)
    # with open(wsl_bat_target / sh_wsl_name, "w") as f: f.write(sh_wsl_content)
    
    # Windows Files
    win_toml_c_path = f"{utils.MUSUBI_PATHS['win_app']}\\TOML\\{toml_win_name}"
    toml_win_content = generate_toml(slug, win_unc_img_path, "win", TARGET_RES)
    bat_win_content = generate_bat(slug, win_toml_c_path, win_toml_c_path)
    
    win_toml_dest = Path(f"{win_toml_target_unc}\\{toml_win_name}".replace("/", "\\"))
    win_bat_dest = Path(f"{win_bat_target_unc}\\{bat_win_name}".replace("/", "\\"))
    
    with open(win_toml_dest, "w") as f: f.write(toml_win_content)
    with open(win_bat_dest, "w") as f: f.write(bat_win_content)

    print(f"✅ Deployment Complete. Bat file: {bat_win_name}")
    
    # Log to Google Sheet
    if trigger_word:
        log_to_sheet(slug, trigger_word)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])
    else:
        print("Usage: python 06_publish.py <slug>")