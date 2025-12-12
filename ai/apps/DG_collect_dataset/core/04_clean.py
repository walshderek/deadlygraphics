import sys
import os
import shutil
from pathlib import Path

# --- BOOTSTRAP PATHS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
import utils

def run(slug):
    path = utils.get_project_path(slug)
    
    # INPUT: 03_validate (The good faces)
    in_dir = path / utils.DIRS['validate']
    
    # OUTPUT: 04_clean (Ready for captioning)
    out_dir = path / utils.DIRS['clean']
    out_dir.mkdir(parents=True, exist_ok=True)

    if not in_dir.exists():
        print(f"❌ Error: Input directory not found: {in_dir}")
        return

    print(f"✨ Cleaning images (Pass-through) from '{in_dir}' -> '{out_dir}'...")

    files = sorted([f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
    
    for i, f in enumerate(files, 1):
        src = in_dir / f
        dst = out_dir / f
        
        if not dst.exists():
            # Placeholder for Watermark Removal Logic
            # For now, we copy the valid face to the clean folder
            shutil.copy(src, dst)

    print(f"✅ Clean Complete. {len(files)} images ready for captioning.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])