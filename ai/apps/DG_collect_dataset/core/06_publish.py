import sys
import os
import shutil
from PIL import Image, ImageOps
from pathlib import Path

# --- BOOTSTRAP PATHS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
import utils

# ================= CONFIGURATION =================
TARGET_SIZE = 1024
RESOLUTIONS = [512, 256]

# --- DESTINATIONS ---
DEST_APP_ROOT = Path("/mnt/c/AI/apps/musubi-tuner")
DEST_TOML_DIR = DEST_APP_ROOT / "files" / "tomls"
DEST_DATASETS_ROOT = DEST_APP_ROOT / "files" / "datasets"

# --- WINDOWS PATHS ---
WIN_TOML_DIR_STR = r"C:\AI\apps\musubi-tuner\files\tomls"
WIN_DATASETS_ROOT_STR = r"C:/AI/apps/musubi-tuner/files/datasets"

# --- MODEL PATHS (LOCAL C:) ---
PATH_T5 = r"C:\AI\models\clip\models_t5_umt5-xxl-enc-bf16.pth"
PATH_VAE = r"C:\AI\models\vae\WAN\wan_2.1_vae.pth"
PATH_DIT_LOW = r"C:\AI\models\diffusion_models\Wan\Wan2.2\14B\Wan_2_2_T2V\fp16\wan2.2_t2v_low_noise_14B_fp16.safetensors"
PATH_DIT_HIGH = r"C:\AI\models\diffusion_models\Wan\Wan2.2\14B\Wan_2_2_T2V\fp16\wan2.2_t2v_high_noise_14B_fp16.safetensors"

def resize_pad_to_square(img_path, save_path, size):
    try:
        with Image.open(img_path) as img:
            img = img.convert("RGB")
            img = ImageOps.pad(img, (size, size), color=(0, 0, 0), centering=(0.5, 0.5))
            img.save(save_path, quality=95)
        return True
    except: return False

def generate_toml(local_windows_path, resolution):
    safe_cache_dir = f"{local_windows_path}_cache"
    return f"""[general]
caption_extension = ".txt"
batch_size = 1
enable_bucket = true
bucket_no_upscale = false
[[datasets]]
image_directory = "{local_windows_path}"
cache_directory = "{safe_cache_dir}"
num_repeats = 1
resolution = [{resolution},{resolution}]
"""

def generate_bat(slug, toml_path_win_c):
    return f"""@echo off
SETLOCAL enabledelayedexpansion

REM --- PATHS ---
set "WAN_ROOT={utils.MUSUBI_PATHS['win_app']}"
set "CFG={toml_path_win_c}"

REM --- OUTPUTS ---
set "OUT=%WAN_ROOT%\\outputs\\{slug}"
set "LOGDIR=%WAN_ROOT%\\logs"
set "OUTNAME={slug}"

REM --- MODELS ---
set "DIT_LOW={PATH_DIT_LOW}"
set "DIT_HIGH={PATH_DIT_HIGH}"
set "VAE={PATH_VAE}"
set "T5={PATH_T5}"

REM --- EXECUTION ---
cd /d "%WAN_ROOT%"
call venv\\scripts\\activate

if not exist "%OUT%" mkdir "%OUT%"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo Starting VAE Latent Cache...
python wan_cache_latents.py --dataset_config "%CFG%" --vae "%VAE%" --vae_dtype float16

echo Starting T5 Cache...
python wan_cache_text_encoder_outputs.py --dataset_config "%CFG%" --t5 "%T5%" --batch_size 16 --fp8_t5

echo Starting Training...
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
  --learning_rate 0.00001 ^
  --logging_dir "%LOGDIR%" ^
  --lr_scheduler cosine ^
  --lr_warmup_steps 100 ^
  --max_data_loader_n_workers 6 ^
  --max_train_epochs 35 ^
  --save_every_n_epochs 5 ^
  --seed 42 ^
  --t5 "%T5%" ^
  --task t2v-A14B ^
  --timestep_boundary 875 ^
  --timestep_sampling logsnr ^
  --vae "%VAE%" ^
  --vae_cache_cpu ^
  --vae_dtype float16 ^
  --network_module networks.lora_wan ^
  --network_dim 16 ^
  --network_alpha 16 ^
  --mixed_precision fp16 ^
  --min_timestep 0 ^
  --max_timestep 1000 ^
  --offload_inactive_dit ^
  --optimizer_type AdamW8bit ^
  --sdpa

pause
ENDLOCAL
"""

def run(slug):
    print(f"=== PUBLISHING {slug} ===")
    config = utils.load_config(slug)
    if not config: return
    
    path = utils.get_project_path(slug)
    
    # 1. Source Images
    clean_dir = path / utils.DIRS.get('clean', '04_clean')
    validate_dir = path / utils.DIRS.get('validate', '03_validate')
    in_dir = clean_dir if clean_dir.exists() else validate_dir
    
    if not in_dir.exists():
        print(f"❌ ERROR: No images found.")
        return

    # 2. Local WSL Output
    publish_root = path / utils.DIRS.get('publish', '06_publish')
    if publish_root.exists(): shutil.rmtree(publish_root)
    publish_root.mkdir(parents=True, exist_ok=True)

    # 3. Windows Destination
    dest_dataset_dir = DEST_DATASETS_ROOT / slug
    if dest_dataset_dir.exists(): shutil.rmtree(dest_dataset_dir)
    dest_dataset_dir.mkdir(parents=True, exist_ok=True)

    print(f"📂 Processing images from: {in_dir}")
    print(f"🚀 Publishing to Windows: {dest_dataset_dir}")

    files = sorted([f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png'))])
    
    # 4. Generate Images & Copy
    res_dir_1024 = publish_root / "1024"
    res_dir_1024.mkdir(exist_ok=True)
    
    TARGET_RES = 256
    
    for f in files:
        if resize_pad_to_square(in_dir / f, res_dir_1024 / f, TARGET_SIZE):
            txt = os.path.splitext(f)[0] + ".txt"
            if (in_dir / txt).exists():
                shutil.copy(in_dir / txt, res_dir_1024 / txt)
        
        for res in RESOLUTIONS:
            if res == 256:
                try:
                    res_dir = publish_root / str(res)
                    res_dir.mkdir(exist_ok=True)
                    img = Image.open(res_dir_1024 / f)
                    img.resize((res, res), Image.Resampling.LANCZOS).save(dest_dataset_dir / f)
                    if (in_dir / txt).exists():
                        shutil.copy(in_dir / txt, dest_dataset_dir / txt)
                except: pass

    # 5. Generate Configs
    win_dataset_path = f"{WIN_DATASETS_ROOT_STR}/{slug}"
    res_str = "256"
    
    toml_name = f"{slug}_{res_str}_win.toml"
    bat_name = f"train_{slug}_{res_str}.bat"
    
    toml_content = generate_toml(win_dataset_path, TARGET_RES)
    bat_content = generate_bat(slug, f"{WIN_TOML_DIR_STR}\\{toml_name}")

    # 6. Deploy
    DEST_TOML_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(DEST_TOML_DIR / toml_name, "w") as f: 
        f.write(toml_content)
    
    with open(DEST_APP_ROOT / bat_name, "w") as f: 
        f.write(bat_content)

    print(f"✅ Images copied to: {dest_dataset_dir}")
    print(f"✅ Configs deployed to Musubi app.")