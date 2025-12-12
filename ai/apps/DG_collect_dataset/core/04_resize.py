import os
import utils
import shutil
from PIL import Image, ImageOps

TARGET_SIZE = 1024

def run(slug):
    path = utils.get_project_path(slug)
    
    # INPUTS: 'crop' (images) and 'caption' (text)
    crop_dir = path / utils.DIRS['crop']
    caption_dir = path / utils.DIRS['caption']
    
    # OUTPUT: 'master'
    master_dir = path / utils.DIRS['master']
    
    if not crop_dir.exists():
        print("❌ Step 2 (Crop) not done.")
        return

    master_dir.mkdir(parents=True, exist_ok=True)
    
    files = [f for f in os.listdir(crop_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    print(f"🖼️  Resizing to Master {TARGET_SIZE}x{TARGET_SIZE}...")
    
    count = 0
    for f in files:
        try:
            # 1. Process Image
            img = Image.open(crop_dir / f).convert("RGB")
            
            # Pad to square (1024x1024)
            # This ensures we don't distort aspect ratio before downsampling
            img_padded = ImageOps.pad(img, (TARGET_SIZE, TARGET_SIZE), color=(0, 0, 0), centering=(0.5, 0.5))
            
            save_name = os.path.splitext(f)[0] + ".jpg"
            img_padded.save(master_dir / save_name, quality=95)
            
            # 2. Copy Caption if it exists
            # We look in the caption dir
            txt_name = os.path.splitext(f)[0] + ".txt"
            src_txt = caption_dir / txt_name
            
            if src_txt.exists():
                shutil.copy(src_txt, master_dir / txt_name)
            
            count += 1
        except Exception as e:
            print(f"    Error {f}: {e}")

    print(f"✅ Master set created: {count} images.")

if __name__ == "__main__":
    run("test_slug")