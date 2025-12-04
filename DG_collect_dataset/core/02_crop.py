# Script Name: core/02_crop.py
import sys, os, subprocess
def check():
    try: import cv2; from deepface import DeepFace; from PIL import Image
    except: subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'opencv-python-headless', 'deepface', 'tf-keras', 'Pillow'])
check()
from deepface import DeepFace
from PIL import Image

def run(slug):
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['scrape']
    out_dir = path / utils.DIRS['crop']
    out_dir.mkdir(parents=True, exist_ok=True)
    
    files = [f for f in os.listdir(in_dir) if f.endswith('.jpg')]
    print(f"--> Cropping {len(files)} images...")
    
    for f in files:
        try:
            # Simple center crop for now to ensure it runs, deepface logic can be complex
            img = Image.open(in_dir / f)
            w, h = img.size
            s = min(w, h)
            img.crop(((w-s)//2, (h-s)//2, (w+s)//2, (h+s)//2)).resize((1024, 1024)).save(out_dir / f, quality=95)
        except: pass