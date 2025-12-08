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
    out_dir.mkdir(parents=True, exist_ok=True)
    
    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
    print(f"--> [02_crop] Processing {len(files)} images...")
    
    count = 0
    for i, f in enumerate(files):
        try:
            img_path = in_dir / f
            img_pil = Image.open(img_path)
            img_pil = ImageOps.exif_transpose(img_pil).convert("RGB")
            cv2_img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            
            faces = DeepFace.extract_faces(img_path=cv2_img, detector_backend='opencv', enforce_detection=False, align=False)
            if not faces: continue
            
            face = max(faces, key=lambda x: x['facial_area']['w'] * x['facial_area']['h'])
            if face['confidence'] < 0.5: continue
                
            fa = face["facial_area"]
            x, y, w, h = int(fa["x"]), int(fa["y"]), int(fa["w"]), int(fa["h"])
            
            center_x, center_y = x + w / 2, y + h / 2
            size = int(max(w, h) * 2.0)
            
            h_img, w_img = cv2_img.shape[:2]
            x1 = max(0, int(center_x - size / 2))
            y1 = max(0, int(center_y - size / 2))
            x2 = min(w_img, int(center_x + size / 2))
            y2 = min(h_img, int(center_y + size / 2))
            
            cropped = cv2_img[y1:y2, x1:x2]
            crop_pil = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))
            
            # FIX: FORCE SQUARE PADDING
            max_side = max(crop_pil.size)
            final_sq = ImageOps.pad(crop_pil, (max_side, max_side), color=(0,0,0), centering=(0.5, 0.5))
            
            save_path = out_dir / f"{os.path.splitext(f)[0]}.jpg"
            final_sq.save(save_path, quality=95)
            count += 1
            if i % 5 == 0: print(f"    Cropped {i}/{len(files)}...")
        except: pass 

    print(f"✅ [02_crop] Complete. {count} images cropped.")