# Script Name: core/04_resize.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Resizes cropped images to a master resolution (1024x1024) with padding if needed.

import sys
import os
import utils
from PIL import Image

TARGET_SIZE = 1024

def resize_pad_to_square(img_path, save_path, target_size=1024):
    try:
        img = Image.open(img_path).convert("RGB")
        img.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
        
        new_img = Image.new("RGB", (target_size, target_size), (0, 0, 0))
        paste_x = (target_size - img.width) // 2
        paste_y = (target_size - img.height) // 2
        new_img.paste(img, (paste_x, paste_y))
        
        new_img.save(save_path, quality=95)
        return True
    except Exception as e:
        print(f"⚠️ Error resizing {os.path.basename(img_path)}: {e}")
        return False

def run(project_slug):
    path = utils.get_project_path(project_slug)
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['master']
    
    if not in_dir.exists():
        print("❌ Run Step 2 (Crop) first.")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🖼️ Resizing to Master {TARGET_SIZE}x{TARGET_SIZE}...")
    
    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    count = 0
    
    for f in files:
        if resize_pad_to_square(in_dir / f, out_dir / f, TARGET_SIZE):
            count += 1
            
    print(f"✅ Master set created: {count} images.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])