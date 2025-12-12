import sys
import os
import shutil
import utils
from PIL import Image, ImageOps
from pathlib import Path

TARGET_SIZE = 1024
RESOLUTIONS = [512, 256]

def resize_pad_to_square(img_path, save_path, size):
    try:
        with Image.open(img_path) as img:
            img = img.convert("RGB")
            img = ImageOps.pad(img, (size, size), color=(0, 0, 0), centering=(0.5, 0.5))
            img.save(save_path, quality=95)
        return True
    except: return False

def generate_toml(clean_path, resolution):
    return f"""[general]
caption_extension = ".txt"
batch_size = 1
enable_bucket = true
bucket_no_upscale = false
[[datasets]]
image_directory = "{clean_path}"
cache_directory = "{clean_path}_cache"
num_repeats = 1
resolution = [{resolution},{resolution}]
"""

def generate_bat(slug, toml_path_win_c):
    return f"""@echo off
set "WAN_ROOT={utils.MUSUBI_PATHS['win_app']}"
set "CFG={toml_path_win_c}"
set "OUT=%WAN_ROOT%\\outputs\\{slug}"
set "LOGDIR=%WAN_ROOT%\\logs"
set "C_MODEL_BASE={utils.MUSUBI_PATHS['win_models']}"
set "DIT_LOW=%C_MODEL_BASE%\\diffusion-models\\Wan\\Wan2.2\\14B\\Wan_2_2_I2V\\fp16\\wan2.2_t2v_low_noise_14B_fp16.safetensors"
set "DIT_HIGH=%C_MODEL_BASE%\\diffusion-models\\Wan\\Wan2.2\\14B\\Wan_2_2_I2V\\fp16\\wan2.2_t2v_high_noise_14B_fp16.safetensors"
set "VAE=%C_MODEL_BASE%\\vae\\wan_2.1_vae.pth"
set "T5=%C_MODEL_BASE%\\clip\\models_t5_umt5-xxl-enc-bf16.pth"
call %WAN_ROOT%\\venv\\scripts\\activate
python wan_cache_latents.py --dataset_config "%CFG%" --vae "%VAE%" --vae_dtype float16 --vae_cache_cpu
python wan_cache_text_encoder_outputs.py --dataset_config "%CFG%" --t5 "%T5%" --batch_size 16 --fp8_t5
accelerate launch --num_processes 1 "wan_train_network.py" ^
  --dataset_config "%CFG%" ^
  --output_dir "%OUT%" ^
  --output_name "{slug}" ^
  --dit "%DIT_LOW%" ^
  --dit_high_noise "%DIT_HIGH%" ^
  --fp8_base ^
  --fp8_scaled ^
  --fp8_t5 ^
  --gradient_accumulation_steps 1 ^
  --learning_rate 0.0001 ^
  --optimizer_type AdamW8bit ^
  --max_train_epochs 35 ^
  --save_every_n_epochs 5 ^
  --t5 "%T5%" ^
  --vae "%VAE%" ^
  --vae_dtype float16 ^
  --timestep_boundary 875 ^
  --timestep_sampling logsnr ^
  --vae_cache_cpu ^
  --persistent_data_loader_workers ^
  --sdpa
pause
"""

def generate_sh(slug, toml_path_wsl):
    return f"""#!/bin/bash
WAN_DIR="{utils.MUSUBI_PATHS['wsl_app']}"
CFG="{toml_path_wsl}"
OUT="${{WAN_DIR}}/outputs/{slug}"
source ${{WAN_DIR}}/venv/bin/activate
accelerate launch --num_processes 1 "wan_train_network.py" \\
  --dataset_config "${{CFG}}" \\
  --output_dir "${{OUT}}" \\
  --output_name "{slug}" \\
  --discrete_flow_shift 3 \\
  --fp8_base \\
  --fp8_scaled \\
  --fp8_t5 \\
  --gradient_accumulation_steps 1 \\
  --learning_rate 0.0001 \\
  --optimizer_type AdamW8bit \\
  --max_train_epochs 35 \\
  --save_every_n_epochs 5 \\
  --t5 "${{T5}}" \\
  --vae "${{VAE}}" \\
  --vae_dtype float16 \\
  --timestep_boundary 875 \\
  --timestep_sampling logsnr \\
  --vae_cache_cpu \\
  --persistent_data_loader_workers \\
  --sdpa
"""

def run(slug):
    print(f"=== PUBLISHING {slug} ===")
    config = utils.load_config(slug)
    if not config: return
    trigger = config['trigger']
    path = utils.get_project_path(slug)
    
    # CHANGE: Read from QC directory
    in_dir = path / utils.DIRS['qc']
    publish_root = path / utils.DIRS['publish']
    if publish_root.exists(): shutil.rmtree(publish_root)
    publish_root.mkdir(parents=True, exist_ok=True)

    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png'))]

    # 1. Master 1024
    res_dir_1024 = publish_root / "1024"
    res_dir_1024.mkdir(exist_ok=True)
    for f in files:
        if resize_pad_to_square(in_dir / f, res_dir_1024 / f, TARGET_SIZE):
            txt = os.path.splitext(f)[0] + ".txt"
            if (in_dir / txt).exists():
                shutil.copy(in_dir / txt, res_dir_1024 / txt)

    # 2. Downsamples
    for res in RESOLUTIONS:
        res_dir = publish_root / str(res)
        res_dir.mkdir(exist_ok=True)
        for f in files:
            try:
                img = Image.open(res_dir_1024 / f)
                img.resize((res, res), Image.Resampling.LANCZOS).save(res_dir / f)
                txt = os.path.splitext(f)[0] + ".txt"
                if (res_dir_1024 / txt).exists():
                    shutil.copy(res_dir_1024 / txt, res_dir / txt)
            except: pass

    # 3. Configs
    TARGET_RES = 256
    res_str = "256"
    wsl_img_path = publish_root / res_str
    win_unc_img_path = utils.get_windows_unc_path(str(wsl_img_path))
    
    toml_win_name = f"{slug}_{res_str}_win.toml"
    bat_win_name = f"train_{slug}_{res_str}.bat"
    win_toml_c_path = f"{utils.MUSUBI_PATHS['win_app']}\\TOML\\{toml_win_name}"
    
    with open(publish_root / toml_win_name, "w") as f:
        f.write(generate_toml(win_unc_img_path, TARGET_RES))
    with open(publish_root / bat_win_name, "w") as f:
        f.write(generate_bat(slug, win_toml_c_path))
    
    try:
        win_toml_dest = Path(f"{utils.get_windows_unc_path(str(Path(utils.MUSUBI_PATHS['wsl_app']) / 'TOML'))}\\{toml_win_name}".replace("/", "\\"))
        win_bat_dest = Path(f"{utils.get_windows_unc_path(str(Path(utils.MUSUBI_PATHS['wsl_app']) / 'BAT'))}\\{bat_win_name}".replace("/", "\\"))
        shutil.copy(publish_root / toml_win_name, win_toml_dest)
        shutil.copy(publish_root / bat_win_name, win_bat_dest)
    except: pass

    with open(publish_root / f"{trigger}.txt", "w") as f:
        f.write(f"Trigger Word = {trigger}")

    print(f"✅ Published to {publish_root}")