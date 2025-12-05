# Script Name: core/02_crop.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Module to detect faces and center-crop images for training.

import sys
import os
import subprocess
from pathlib import Path

# --- Module Dependency Check (Self-Healing) ---
def check_deps():
    missing = []
    
    # Check for core dependencies
    try: import cv2
    except ImportError: missing.append("opencv-python-headless")
    
    try: import numpy as np
    except ImportError: missing.append("numpy")
    
    try: from deepface import DeepFace
    except ImportError: missing.extend(["deepface", "tf-keras"])
    
    try: from PIL import Image
    except ImportError: missing.append("Pillow")

    if missing:
        print(f"--> [02_crop] Installing missing deps: {', '.join(missing)}")
        try:
            # Install into the current active environment
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
            print("--> [02_crop] Deps installed.")
        except Exception as e:
            print(f"❌ [02_crop] Install failed: {e}. Run manually: pip install {' '.join(missing)}")
            sys.exit(1)

# Run check immediately so subsequent imports succeed
check_deps()

# Now safe to import
import cv2
from deepface import DeepFace
from PIL import Image

def run(slug):
    """
    Main entry point for Step 2.
    slug: The folder name (e.g. 'Phil_Gacha')
    """
    print(f"--> [02_crop] Running crop logic for: {slug}")
    
    # Placeholder path resolution (needs refinement based on your utils.py)
    # For now, we assume the folder is created by Step 1 in the standard output location
    base_dir = Path(f"/mnt/h/My Drive/AI/Datasets/{slug}")
    if not base_dir.exists():
        base_dir = Path(f"datasets/{slug}") # Local fallback

    if not base_dir.exists():
        print(f"❌ [02_crop] Directory not found: {base_dir}")
        return

    images = [f for f in os.listdir(base_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"--> [02_crop] Found {len(images)} images to process.")

    # (Face detection and cropping logic would follow here)
    # ...
    
    print("✅ [02_crop] Cropping complete.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])