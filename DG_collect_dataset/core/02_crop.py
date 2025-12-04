import sys
import os
import cv2
import numpy as np
from deepface import DeepFace
from PIL import Image, ImageOps
import utils

def run(project_slug):
    path = utils.get_project_path(project_slug)
    in_dir = path / utils.DIRS['scrape']
    out_dir = path / utils.DIRS['crop']
    
    if not in_dir.exists():
        print(f"❌ ERROR: Input directory missing: {in_dir}")
        return

    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    if not files:
        print(f"⚠️  WARNING: No images found in {in_dir}")
        print(f"   Did the scraper download anything?")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"✂️  Processing {len(files)} images for {project_slug}...")
    
    count = 0
    success = 0
    
    for f in files:
        count += 1
        img_path = str(in_dir / f)
        save_path = str(out_dir / f)
        
        try:
            # Load Image
            img_pil = Image.open(img_path)
            img_pil = ImageOps.exif_transpose(img_pil).convert("RGB")
            cv2_img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            
            # Detect Face
            faces = DeepFace.extract_faces(
                img_path=cv2_img, 
                detector_backend='opencv', 
                enforce_detection=False, 
                align=False
            )
            
            # Find Largest Face
            face = max(faces, key=lambda x: x['facial_area']['w'] * x['facial_area']['h'])
            if face['confidence'] < 0.5: continue # Skip low confidence

            # Crop Logic (Square)
            fa = face["facial_area"]
            x, y, w, h = int(fa["x"]), int(fa["y"]), int(fa["w"]), int(fa["h"])
            
            center_x, center_y = x + w/2, y + h/2
            size = int(max(w, h) * 2.0) # Zoom factor 2.0
            
            h_img, w_img, _ = cv2_img.shape
            x1 = max(0, int(center_x - size/2))
            y1 = max(0, int(center_y - size/2))
            x2 = min(w_img, int(center_x + size/2))
            y2 = min(h_img, int(center_y + size/2))
            
            cropped = cv2_img[y1:y2, x1:x2]
            
            # Save
            Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)).save(save_path, quality=95)
            success += 1
            
            if count % 5 == 0: print(f"   Processed {count}/{len(files)}...")
            
        except Exception as e:
            pass

    print(f"✅ Cropped {success} faces from {count} images.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])