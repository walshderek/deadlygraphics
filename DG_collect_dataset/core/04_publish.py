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
call %WAN_ROOT%\\venv\\scripts\\activate
accelerate launch --num_processes 1 "wan_train_network.py" --dataset_config "%CFG%" --output_dir "%OUT%" --output_name "{slug}"
"""

def generate_sh(slug, toml_path_wsl):
    return f"""#!/bin/bash
WAN_DIR="{utils.MUSUBI_PATHS['wsl_app']}"
CFG="{toml_path_wsl}"
OUT="${{WAN_DIR}}/outputs/{slug}"
source ${{WAN_DIR}}/venv/bin/activate
accelerate launch --num_processes 1 "wan_train_network.py" --dataset_config "${{CFG}}" --output_dir "${{OUT}}" --output_name "{slug}"
"""

def run(slug):
    config = utils.load_config(slug)
    trigger = config['trigger']
    path = utils.get_project_path(slug)
    
    in_dir = path / utils.DIRS['crop']
    caption_dir = path / utils.DIRS['caption']
    publish_root = path / utils.DIRS['publish']
    publish_root.mkdir(parents=True, exist_ok=True)
    
    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png'))]
    
    # 1. Master 1024
    res_dir_1024 = publish_root / "1024"
    res_dir_1024.mkdir(exist_ok=True)
    for f in files:
        if resize_pad_to_square(in_dir / f, res_dir_1024 / f, TARGET_SIZE):
            txt = os.path.splitext(f)[0] + ".txt"
            if (caption_dir / txt).exists():
                shutil.copy(caption_dir / txt, res_dir_1024 / txt)

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

    # 3. Configs for 256
    TARGET_RES = 256
    res_str = "256"
    
    wsl_img_path = publish_root / res_str
    if not wsl_img_path.exists(): return

    # WSL Targets
    wsl_toml_target = Path(utils.MUSUBI_PATHS['wsl_app']) / "TOML"
    wsl_bat_target = Path(utils.MUSUBI_PATHS['wsl_app']) / "BAT"
    wsl_toml_target.mkdir(exist_ok=True)
    wsl_bat_target.mkdir(exist_ok=True)

    # Windows UNC Targets
    win_toml_target_unc = utils.get_windows_unc_path(str(wsl_toml_target))
    win_bat_target_unc = utils.get_windows_unc_path(str(wsl_bat_target))
    win_unc_img_path = utils.get_windows_unc_path(str(wsl_img_path))

    # Filenames
    toml_wsl_name = f"{slug}_{res_str}_wsl.toml"
    sh_wsl_name = f"train_{slug}_{res_str}.sh"
    toml_win_name = f"{slug}_{res_str}_win.toml"
    bat_win_name = f"train_{slug}_{res_str}.bat"

    # Write Files
    toml_wsl_content = generate_toml(str(wsl_img_path), TARGET_RES)
    with open(wsl_toml_target / toml_wsl_name, "w") as f: f.write(toml_wsl_content)
    
    sh_wsl_content = generate_sh(slug, str(wsl_toml_target / toml_wsl_name))
    with open(wsl_bat_target / sh_wsl_name, "w") as f: f.write(sh_wsl_content)
    os.chmod(wsl_bat_target / sh_wsl_name, 0o755)

    win_toml_c_path = f"{utils.MUSUBI_PATHS['win_app']}\\TOML\\{toml_win_name}"
    toml_win_content = generate_toml(win_unc_img_path, TARGET_RES)
    bat_win_content = generate_bat(slug, win_toml_c_path)

    win_toml_dest = Path(f"{win_toml_target_unc}\\{toml_win_name}".replace("/", "\\"))
    win_bat_dest = Path(f"{win_bat_target_unc}\\{bat_win_name}".replace("/", "\\"))
    
    try:
        with open(win_toml_dest, "w") as f: f.write(toml_win_content)
        with open(win_bat_dest, "w") as f: f.write(bat_win_content)
    except Exception as e:
        print(f"⚠️ Could not write to Windows UNC paths: {e}")

    # Local Copies
    shutil.copy(wsl_toml_target / toml_wsl_name, publish_root / toml_wsl_name)
    shutil.copy(wsl_bat_target / sh_wsl_name, publish_root / sh_wsl_name)
    # Just write the win contents locally for backup
    with open(publish_root / toml_win_name, "w") as f: f.write(toml_win_content)
    with open(publish_root / bat_win_name, "w") as f: f.write(bat_win_content)

    # Trigger Info
    with open(publish_root / f"{trigger}.txt", "w") as f:
        f.write(f"Trigger Word = {trigger}")

    print(f"✅ Published to {publish_root}")