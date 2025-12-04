# Script Name: DG_collect_dataset.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: AI Dataset Factory. Orchestrates modules. Installs ALL dependencies on first run.

import sys
import os
import argparse
import importlib
import subprocess
from pathlib import Path
import platform

# --- Configuration ---
DEFAULT_SEARCH_TERM = "portrait photo"
TRIGGER_WORD = "ohwx"
MAX_IMAGES = 50

# --- PATH SETUP ---
CORE_DIR = Path(__file__).parent / "core"
sys.path.append(str(CORE_DIR))

# --- Dependency Management (THE FINAL FIX) ---
def check_and_install_dependencies():
    """Aggressively checks and installs all dependencies needed by all core modules."""
    required = [
        'requests', 'tqdm', 'beautifulsoup4', 'Pillow', 
        'opencv-python-headless', 'torch', 'transformers', 
        'einops', 'accelerate', 'qwen_vl_utils', 
        'gspread', 'oauth2client', 'google-auth-oauthlib', 'google-auth-httplib2',
        'deepface', 'pandas', 'numpy', 'tf-keras'
    ]
    
    missing = []
    for pkg in required:
        try:
            # We only check the base package name here to see if it's installed
            import_name = pkg.split('-')[0].split('<')[0]
            if import_name == 'opencv': import_name = 'cv2'
            if import_name == 'beautifulsoup4': import_name = 'bs4'
            if import_name == 'Pillow': import_name = 'PIL'
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        print(f"--> Installing missing dependencies: {', '.join(missing)}")
        try:
            # Install all missing packages in one go.
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'] + missing)
            print("--> Dependencies installed.")
        except:
            print("\n❌ CRITICAL: Auto-install failed.")
            print(f"Run manually: {sys.executable} -m pip install {' '.join(missing)}")
            sys.exit(1)

# --- 2. BOOTSTRAP ---
# Run check immediately to prevent deepface/cv2 crash on import
check_and_install_dependencies()

# --- 3. DYNAMIC MODULE LOADING ---
def load_core_module(module_name):
    try:
        return importlib.import_module(module_name)
    except ImportError as e:
        print(f"❌ Error importing 'core/{module_name}.py': {e}")
        sys.exit(1)

# Import dependencies after check (to prevent crash)
import utils
# Load Steps
mod_scrape     = load_core_module("01_setup_scrape")
mod_crop       = load_core_module("02_crop")
mod_caption    = load_core_module("03_caption")
mod_resize     = load_core_module("04_resize")
mod_downsample = load_core_module("05_downsample")
mod_publish    = load_core_module("06_publish")

# --- 4. PIPELINE ---
def run_pipeline(args):
    print(f"🚀 Pipeline Started: {args.name}")
    
    try: slug = utils.slugify(args.name)
    except: slug = args.name.replace(" ", "_")

    all_steps = [1, 2, 3, 4, 5, 6]
    if args.steps:
        selected = []
        for s in args.steps:
            parts = str(s).split(',')
            for p in parts:
                if '-' in p:
                    start, end = map(int, p.split('-'))
                    selected.extend(range(start, end + 1))
                else: selected.append(int(p))
        all_steps = selected

    # Step 1: Scrape
    if 1 in all_steps:
        print("\n=== 01: SETUP & SCRAPE ===")
        try: slug = mod_scrape.run(args.name, args.count)
        except: slug = mod_scrape.run(args.name, args.count)
        if not slug: return

    # Step 2: Crop
    if 2 in all_steps:
        print("\n=== 02: CROP ===")
        mod_crop.run(slug)

    # Step 3: Caption
    if 3 in all_steps:
        print("\n=== 03: CAPTION ===")
        mod_caption.run(slug, trigger_word=args.trigger, model_name=args.model, style=args.style)

    # Step 4: Resize
    if 4 in all_steps:
        print("\n=== 04: RESIZE MASTER ===")
        mod_resize.run(slug)

    # Step 5: Downsample
    if 5 in all_steps:
        print("\n=== 05: DOWNSAMPLE ===")
        mod_downsample.run(slug)
    
    # Step 6: Publish
    if 6 in all_steps:
        print("\n=== 06: PUBLISH ===")
        mod_publish.run(slug, trigger_word=args.trigger, model_name=args.model)
    
    print(f"\n✅ ALL DONE: {args.name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", help="Subject Full Name")
    parser.add_argument("--count", type=int, default=50, help="Max images")
    parser.add_argument("--gender", choices=["m", "f"], help="Gender (optional)")
    parser.add_argument("--trigger", default="ohwx", help="Trigger word")
    parser.add_argument("--model", choices=["moondream", "qwen"], default="moondream", help="LLM Model")
    parser.add_argument("--style", default="crinklypaper", help="Caption Style")
    parser.add_argument("steps", nargs="*", help="Steps (e.g. 1 3-5)")
    
    args = parser.parse_args()

    if not args.name:
        print("Usage: DG_collect_dataset 'Subject Name' [options]")
        sys.exit(1)

    run_pipeline(args)