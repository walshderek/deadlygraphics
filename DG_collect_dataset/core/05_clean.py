import sys
import os
import cv2
import utils
import shutil

def run(slug):
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['caption'] # Note: We read image from crop, txt from caption
    # But files are separated. We need images from crop.
    img_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['clean']
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🧹 Cleaning images for {slug}...")
    
    files = [f for f in os.listdir(img_dir) if f.lower().endswith('.jpg')]
    
    for f in files:
        img_path = img_dir / f
        save_path = out_dir / f
        
        # 1. Load
        img = cv2.imread(str(img_path))
        
        # 2. Simple Inpaint (Stretch Goal Placeholder for Stable Diffusion)
        # We start with basic OpenCV inpainting for speed/reliability
        # A full SD implementation would load the pipeline here.
        
        # For now, we just copy to ensure pipeline flow
        # To enable SD:
        # pipe = StableDiffusionInpaintPipeline.from_pretrained(...)
        # mask = ...
        # img = pipe(prompt="clean background", image=img, mask_image=mask).images[0]
        
        shutil.copy(img_path, save_path)
        
        # Copy caption too
        txt_name = os.path.splitext(f)[0] + ".txt"
        src_txt = path / utils.DIRS['caption'] / txt_name
        if src_txt.exists():
            shutil.copy(src_txt, out_dir / txt_name)
            
    print("✅ Clean step complete.")