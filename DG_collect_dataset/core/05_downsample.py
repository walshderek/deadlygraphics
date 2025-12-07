"""
Script Name: 05_downsample.py
Author: DeadlyGraphics
Date: 2025-12-06
"""

import os
from pathlib import Path
from PIL import Image, ImageOps

def run(slug, trigger_word):
    print(f"=== 05 DOWNSAMPLE: Processing for {slug} ===")
    
    base_dir = Path.cwd()
    
    # CORRECT INPUT: outputs/slug/03_master_1024
    master_dir = base_dir / "outputs" / slug / "03_master_1024"
    
    # CORRECT OUTPUT: outputs/slug/05_downsample
    downsample_base = base_dir / "outputs" / slug / "05_downsample"
    
    sizes = [1024, 512, 256]

    if not master_dir.exists():
        print(f"❌ Error: Master directory not found at {master_dir}")
        return

    # Create 256, 512, 1024 folders and cache folders
    for size in sizes:
        (downsample_base / str(size)).mkdir(parents=True, exist_ok=True)
        (downsample_base / f"{size}_cache").mkdir(parents=True, exist_ok=True)

    images = [f for f in os.listdir(master_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    
    if not images:
        print("❌ Error: No images found in master directory.")
        return

    for img_name in images:
        img_path = master_dir / img_name
        txt_name = img_path.stem + ".txt"
        txt_path = master_dir / txt_name

        try:
            with Image.open(img_path) as img:
                img = img.convert("RGB")

                # --- TRIGGER WORD INJECTION ---
                final_caption = ""
                if txt_path.exists():
                    with open(txt_path, 'r', encoding='utf-8') as f:
                        existing_caption = f.read().strip()
                    
                    if trigger_word and trigger_word.lower() not in existing_caption.lower():
                        final_caption = f"{trigger_word}, {existing_caption}"
                    else:
                        final_caption = existing_caption
                else:
                    final_caption = trigger_word

                # Save to 256, 512, 1024 folders
                for size in sizes:
                    # Resize
                    processed_img = ImageOps.fit(img, (size, size), method=Image.Resampling.LANCZOS)
                    
                    # Save Image
                    save_dir = downsample_base / str(size)
                    processed_img.save(save_dir / img_name, quality=95)
                    
                    # Save Text with Trigger Word
                    with open(save_dir / txt_name, 'w', encoding='utf-8') as f:
                        f.write(final_caption)

        except Exception as e:
            print(f"⚠️ Error processing {img_name}: {e}")

    print(f"✅ Downsampling Complete. Folders created at: {downsample_base}")

if __name__ == "__main__":
    run("ed_milliband", "ohwx")