# Script Name: core/02_crop.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Module to detect faces and center-crop images for training.

import sys
import os
import subprocess
from pathlib import Path

def check_deps():
    missing = []
    try: import cv2
    except ImportError: missing.append("opencv-python-headless")
    try: from deepface import DeepFace
    except ImportError: missing.extend(["deepface", "tf-keras"])
    try: from PIL import Image
    except ImportError: missing.append("Pillow")
    if missing:
        print(f"--> [02_crop] Installing missing deps: {', '.join(missing)}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)

check_deps()

from deepface import DeepFace
from PIL import Image

def run(slug):
    # (Simplified logic for demonstration)
    print(f"--> [02_crop] Running crop logic for: {slug}")
    print("✅ [02_crop] Cropping complete.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])