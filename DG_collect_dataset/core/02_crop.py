# Script Name: core/02_crop.py
import sys
import os
import subprocess
import utils
from pathlib import Path

# Dependency Check
def check_deps():
    missing = []
    try: import cv2
    except: missing.append("opencv-python-headless")
    try: from deepface import DeepFace
    except: missing.extend(["deepface", "tf-keras", "numpy", "pandas"])
    
    if missing:
        print(f"--> [02_crop] Installing missing deps: {', '.join(missing)}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)

check_deps()
from deepface import DeepFace
from PIL import Image

def run(slug):
    print(f"--> [02_crop] Processing: {slug}")
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['scrape']
    out_dir = path / utils.DIRS['crop']
    out_dir.mkdir(parents=True, exist_ok=True)
    
    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png'))]
    
    for f in files:
        img_path = str(in_dir / f)
        save_path = str(out_dir / f)
        
        try:
            # DeepFace extraction (Smart Crop)
            faces = DeepFace.extract_faces(img_path=img_path, detector_backend='opencv', enforce_detection=False)
            
            img = Image.open(img_path).convert("RGB")
            
            if faces:
                # Use first face
                face = faces[0]['facial_area']
                x, y, w, h = face['x'], face['y'], face['w'], face['h']
                cx, cy = x + w//2, y + h//2
                
                # 1024 crop centered on face
                sz = 1024
                left = max(0, cx - sz//2)
                top = max(0, cy - sz//2)
                img = img.crop((left, top, left+sz, top+sz))
            
            # Ensure it is exactly 1024x1024 (resize/pad if needed)
            img = img.resize((1024, 1024), Image.LANCZOS)
            img.save(save_path, "JPEG", quality=95)
            
        except Exception as e:
            print(f"   Skip {f}: {e}")
            
    print(f"✅ [02_crop] Complete.")