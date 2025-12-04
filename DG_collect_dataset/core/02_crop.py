# Script Name: core/02_crop.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Module to detect faces and center-crop images for training.

import sys
import os
import subprocess
import logging

# --- Module Dependency Check ---
def check_deps():
    missing = []
    try: import cv2
    except ImportError: missing.append("opencv-python-headless")
    
    try: from deepface import DeepFace
    except ImportError: missing.extend(["deepface", "tf-keras"])
    
    try: import numpy
    except ImportError: missing.append("numpy")
    
    try: from PIL import Image
    except ImportError: missing.append("Pillow")

    if missing:
        print(f"--> [02_crop] Installing missing deps: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
            print("--> [02_crop] Deps installed.")
        except Exception as e:
            print(f"❌ [02_crop] Install failed: {e}")
            sys.exit(1)

# Run check immediately
check_deps()

# Now safe to import
import cv2
from deepface import DeepFace
import numpy as np
from PIL import Image

def run(slug):
    """
    Main entry point for Step 2.
    slug: The folder name (e.g. 'Phil_Gacha')
    """
    print(f"--> [02_crop] Running crop logic for: {slug}")
    
    # Determine paths based on OS
    if os.name == 'nt':
        base_dir = f"H:\\My Drive\\AI\\Datasets\\{slug}"
    else:
        base_dir = f"/mnt/h/My Drive/AI/Datasets/{slug}"
        if not os.path.exists(base_dir):
            # Fallback to local datasets if H: not mounted
            base_dir = f"datasets/{slug}"

    if not os.path.exists(base_dir):
        print(f"❌ [02_crop] Directory not found: {base_dir}")
        return

    images = [f for f in os.listdir(base_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"--> [02_crop] Found {len(images)} images to process.")

    for img_file in images:
        img_path = os.path.join(base_dir, img_file)
        
        try:
            # 1. Detect Face using DeepFace (backend=opencv is fastest)
            # This returns a list of faces. We take the first/largest.
            # enforce_detection=False prevents crash if no face found.
            faces = DeepFace.extract_faces(img_path=img_path, detector_backend='opencv', enforce_detection=False)
            
            if faces:
                # Get the most prominent face area
                face = faces[0]['facial_area']
                x, y, w, h = face['x'], face['y'], face['w'], face['h']
                
                # Load full image
                pil_img = Image.open(img_path).convert("RGB")
                width, height = pil_img.size
                
                # Calculate center of face
                center_x = x + (w // 2)
                center_y = y + (h // 2)
                
                # Determine crop box (1024x1024 or largest square possible)
                # For now, let's try to keep it simple: Center on face, max square
                crop_size = min(width, height)
                
                left = max(0, center_x - (crop_size // 2))
                top = max(0, center_y - (crop_size // 2))
                right = left + crop_size
                bottom = top + crop_size
                
                # Adjust if out of bounds
                if right > width:
                    right = width
                    left = width - crop_size
                if bottom > height:
                    bottom = height
                    top = height - crop_size
                
                # Crop
                pil_img = pil_img.crop((left, top, right, bottom))
                
                # Resize to 1024x1024
                pil_img = pil_img.resize((1024, 1024), Image.LANCZOS)
                
                # Overwrite
                pil_img.save(img_path, "JPEG", quality=95)
                # print(f"    Processed: {img_file}")
            
            else:
                print(f"    No face in {img_file}, skipping smart crop.")
                
        except Exception as e:
            print(f"    Error processing {img_file}: {e}")

if __name__ == "__main__":
    # Allow running this module standalone for testing
    if len(sys.argv) > 1:
        run(sys.argv[1])
    else:
        print("Usage: python 02_crop.py <slug>")