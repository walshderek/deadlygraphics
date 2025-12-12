import sys
import os
import shutil
import utils
from PIL import Image

RESOLUTIONS = [512, 256]

def run(project_slug):
    path = utils.get_project_path(project_slug)
    
    # Input: Master (1024)
    in_dir = path / utils.DIRS['master']
    # Output: Downsample folder
    down_root = path / utils.DIRS['downsample']
    # Captions Source: 02_captions
    caption_dir = path / utils.DIRS['caption']
    
    if not in_dir.exists():
        print("❌ Run Step 4 (Resize) first.")
        return

    print(f"📉 Downsampling to {RESOLUTIONS}...")
    
    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    
    for res in RESOLUTIONS:
        res_dir = down_root / str(res)
        res_dir.mkdir(parents=True, exist_ok=True)
        
        count = 0
        for f in files:
            try:
                # 1. Resize Image (LANCZOS, No Crop)
                img = Image.open(in_dir / f)
                img_res = img.resize((res, res), Image.Resampling.LANCZOS)
                img_res.save(res_dir / f, quality=95)
                
                # 2. Copy Caption from Source
                txt_name = os.path.splitext(f)[0] + ".txt"
                src_txt = caption_dir / txt_name
                
                if src_txt.exists():
                    shutil.copy(src_txt, res_dir / txt_name)
                
                count += 1
            except Exception as e:
                print(f"Error {f}: {e}")
        
        print(f"   ➜ {res}x{res}: {count} images")

    print("✅ Downsampling complete.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])