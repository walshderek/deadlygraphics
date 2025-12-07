import sys
import os
import cv2
import numpy as np
from deepface import DeepFace
from PIL import Image, ImageOps
import utils

def run(slug):
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['scrape']
    out_dir = path / utils.DIRS['crop']
    
    if not in_dir.exists():
        print(f"❌ No scraped images found at {in_dir}")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
    print(f"--> [02_crop] Processing {len(files)} images for: {slug}")
    
    count = 0
    for i, f in enumerate(files):
        try:
            img_path = in_dir / f
            
            # Load with PIL to handle EXIF rotation
            img_pil = Image.open(img_path)
            img_pil = ImageOps.exif_transpose(img_pil)
            img_pil = img_pil.convert("RGB")
            
            # Convert to CV2 BGR
            cv2_img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            
            # Detect Faces
            faces = DeepFace.extract_faces(
                img_path=cv2_img, 
                detector_backend='opencv', 
                enforce_detection=False, 
                align=False
            )
            
            if not faces: continue
            
            # Find largest face
            face = max(faces, key=lambda x: x['facial_area']['w'] * x['facial_area']['h'])
            
            if face['confidence'] < 0.5:
                continue
                
            fa = face["facial_area"]
            x, y, w, h = int(fa["x"]), int(fa["y"]), int(fa["w"]), int(fa["h"])
            
            # Dynamic Zoom Crop (2.0x)
            center_x = x + w / 2
            center_y = y + h / 2
            size = int(max(w, h) * 2.0)
            
            h_img, w_img = cv2_img.shape[:2]
            
            x1 = max(0, int(center_x - size / 2))
            y1 = max(0, int(center_y - size / 2))
            x2 = min(w_img, int(center_x + size / 2))
            y2 = min(h_img, int(center_y + size / 2))
            
            cropped = cv2_img[y1:y2, x1:x2]
            
            # Save
            save_path = out_dir / f"{os.path.splitext(f)[0]}.jpg"
            Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)).save(save_path, quality=95)
            count += 1
            
            if i % 5 == 0: print(f"    Cropped {i}/{len(files)}...")

        except Exception as e:
            pass # Skip image on error

    print(f"✅ [02_crop] Complete. {count} images cropped.")