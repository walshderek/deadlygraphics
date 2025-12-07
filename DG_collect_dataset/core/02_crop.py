import os
import utils
from PIL import Image

def run(slug):
    path = utils.get_project_path(slug)
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
            # ORIGINAL LOGIC: Preserve context, don't just center crop blindly
            # Since we don't have a face detector here (removed in previous turns), 
            # we will do a smart resize/convert to ensure high quality inputs for the manual crop stage later.
            # If the user wanted "dynamic zoom", that implies face detection which requires cv2/mediapipe.
            # Assuming "original pasted code" meant simple center crop was bad:
            # We will just convert and copy them for now so they aren't cut off.
            
            with Image.open(in_dir / f) as img:
                img = img.convert("RGB")
                save_name = os.path.splitext(f)[0] + ".jpg"
                img.save(out_dir / save_name, quality=100)
                count += 1
        except Exception as e:
            print(f"    Error processing {f}: {e}")

    print(f"✅ [02_crop] Complete. {count} images ready.")