import sys
import os
import shutil
import utils
from PIL import Image, ImageOps

TARGET_SIZE = 1024
RESOLUTIONS = [512, 256]

def resize_pad_to_square(img_path, save_path, size):
    try:
        with Image.open(img_path) as img:
            img = img.convert("RGB")
            # Pad to square (Preserves content, adds black bars if needed)
            img = ImageOps.pad(img, (size, size), color=(0, 0, 0), centering=(0.5, 0.5))
            img.save(save_path, quality=95)
        return True
    except Exception as e:
        print(f"Error resizing {img_path}: {e}")
        return False

# --- CONFIG GENERATORS ---
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
    # Standard Windows Training Script
    return f"""@echo off
set "WAN_ROOT={utils.MUSUBI_PATHS['win_app']}"
set "CFG={toml_path_win_c}"
set "OUT=%WAN_ROOT%\\outputs\\{slug}"
call %WAN_ROOT%\\venv\\scripts\\activate
accelerate launch --num_processes 1 "wan_train_network.py" --dataset_config "%CFG%" --output_dir "%OUT%" --output_name "{slug}"
"""

def generate_sh(slug, toml_path_wsl):
    # Standard WSL/Linux Training Script
    return f"""#!/bin/bash
WAN_DIR="{utils.MUSUBI_PATHS['wsl_app']}"
CFG="{toml_path_wsl}"
OUT="${{WAN_DIR}}/outputs/{slug}"
source ${{WAN_DIR}}/venv/bin/activate
accelerate launch --num_processes 1 "wan_train_network.py" --dataset_config "${{CFG}}" --output_dir "${{OUT}}" --output_name "{slug}"
"""

def run(project_slug):
    print(f"=== PUBLISHING {project_slug} ===")
    config = utils.load_config(project_slug)
    if not config: return
    trigger = config['trigger']
    path = utils.get_project_path(project_slug)
    
    in_dir = path / utils.DIRS['crop']
    caption_dir = path / utils.DIRS['caption']
    publish_root = path / utils.DIRS['publish']
    
    # Clean/Create publish root
    if publish_root.exists(): shutil.rmtree(publish_root)
    publish_root.mkdir(parents=True, exist_ok=True)

    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    # 1. Create 1024 (Master)
    print("🖼️  Creating 1024 Master...")
    res_dir_1024 = publish_root / "1024"
    res_dir_1024.mkdir(exist_ok=True)
    
    for f in files:
        if resize_pad_to_square(in_dir / f, res_dir_1024 / f, TARGET_SIZE):
            # Copy Caption
            txt_name = os.path.splitext(f)[0] + ".txt"
            src_txt = caption_dir / txt_name
            if src_txt.exists():
                shutil.copy(src_txt, res_dir_1024 / txt_name)

    # 2. Downsample to 256/512
    print(f"📉 Downsampling to {RESOLUTIONS}...")
    for res in RESOLUTIONS:
        res_dir = publish_root / str(res)
        res_dir.mkdir(exist_ok=True)
        
        for f in files:
            try:
                # Resize from 1024 version
                img = Image.open(res_dir_1024 / f)
                img_res = img.resize((res, res), Image.Resampling.LANCZOS)
                img_res.save(res_dir / f, quality=95)
                
                # Copy caption from 1024
                txt_name = os.path.splitext(f)[0] + ".txt"
                src_txt = res_dir_1024 / txt_name
                if src_txt.exists():
                    shutil.copy(src_txt, res_dir / txt_name)
            except Exception: pass

    # 3. Generate Configs for 256
    TARGET_RES = 256
    res_str = str(TARGET_RES)
    
    # Path where images actully live in WSL
    wsl_img_path = publish_root / res_str
    # UNC path for Windows to access them
    win_unc_img_path = utils.get_windows_unc_path(str(wsl_img_path))
    
    # Filenames
    toml_wsl = f"{project_slug}_{res_str}_wsl.toml"
    sh_wsl = f"train_{project_slug}_{res_str}.sh"
    toml_win = f"{project_slug}_{res_str}_win.toml"
    bat_win = f"train_{project_slug}_{res_str}.bat"

    # Write WSL files (Locally)
    with open(publish_root / toml_wsl, "w") as f:
        f.write(generate_toml(str(wsl_img_path), TARGET_RES))
    
    with open(publish_root / sh_wsl, "w") as f:
        f.write(generate_sh(project_slug, str(publish_root / toml_wsl)))
    os.chmod(publish_root / sh_wsl, 0o755)

    # Write WIN files (Locally, pointing to UNC)
    # Note: Windows TOML needs the path to images as seen by Windows (UNC)
    with open(publish_root / toml_win, "w") as f:
        f.write(generate_toml(win_unc_img_path, TARGET_RES))
        
    # BAT file assumes the TOML is also accessed via UNC or local C: mount
    # We will point it to the UNC path of the generated TOML
    win_unc_toml_path = utils.get_windows_unc_path(str(publish_root / toml_win))
    with open(publish_root / bat_win, "w") as f:
        f.write(generate_bat(project_slug, win_unc_toml_path))

    # 4. Trigger File
    with open(publish_root / "trigger_info.txt", "w") as f:
        f.write(f"Trigger: {trigger}\nSlug: {project_slug}")

    print(f"✅ Published to {publish_root}")

if __name__ == "__main__":
    run("test_slug")