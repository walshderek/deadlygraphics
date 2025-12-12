import sys
import os
import shutil
import time
from pathlib import Path

# --- BOOTSTRAP PATHS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
import utils

# Try importing DeepFace for validation
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    utils.install_package("deepface tf-keras opencv-python")
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True

def validate_image(img_path, target_gender):
    if not DEEPFACE_AVAILABLE:
        return True 

    try:
        # Check if exactly one face exists
        faces = DeepFace.extract_faces(
            img_path=str(img_path), 
            detector_backend='opencv', 
            enforce_detection=True, 
            align=False
        )
        return len(faces) == 1
    except:
        return False

def run(slug):
    config = utils.load_config(slug)
    if not config: return

    gender = config.get('gender', 'm')
    path = utils.get_project_path(slug)
    
    # INPUT: 02_crop
    in_dir = path / utils.DIRS['crop']
    
    # OUTPUT: 03_validate
    out_dir = path / utils.DIRS['validate']
    out_dir.mkdir(parents=True, exist_ok=True)

    if not in_dir.exists():
        print(f"❌ Error: Input directory not found: {in_dir}")
        return

    print(f"🔍 Validating images in '{in_dir}'...")

    files = sorted([f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
    valid_count = 0
    
    for i, f in enumerate(files, 1):
        src = in_dir / f
        dst = out_dir / f
        
        if dst.exists():
            valid_count += 1
            continue
            
        print(f"   [{i}/{len(files)}] Checking {f}...", end="", flush=True)
        if validate_image(src, gender):
            shutil.copy(src, dst)
            print(" ✅ Valid")
            valid_count += 1
        else:
            print(" ❌ Rejected")

    print(f"✅ Validation Complete. {valid_count} images passed.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])