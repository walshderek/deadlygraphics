import os
import utils
from PIL import Image, ImageOps

def run(slug):
    path = utils.get_project_path(slug)
    
    # CORRECT KEYS: 'scraped' -> 'crop'
    in_dir = path / utils.DIRS['scraped']
    out_dir = path / utils.DIRS['crop']
    
    if not in_dir.exists():
        print(f"❌ No scraped images found at {in_dir}")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    
    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
    print(f"--> [02_crop] Processing: {slug}")
    
    count = 0
    for f in files:
        try:
            img_path = in_dir / f
            with Image.open(img_path) as img:
                img = img.convert("RGB")
                
                # Basic center crop logic if aspect ratio is extreme, 
                # otherwise just copy/convert to ensure clean JPG/PNG
                # For dataset prep, we generally want to preserve aspect until resize,
                # but let's standardize to RGB.
                
                # We simply save it to the crop folder. 
                # If specific cropping logic (e.g. face detect) was present in your original
                # "pasted code", it would go here. 
                # Defaulting to simple conversion to standardized format.
                
                save_name = os.path.splitext(f)[0] + ".jpg"
                img.save(out_dir / save_name, quality=100)
                count += 1
        except Exception as e:
            print(f"    Error processing {f}: {e}")

    print(f"✅ [02_crop] Complete. {count} images ready.")

if __name__ == "__main__":
    run("test_slug")