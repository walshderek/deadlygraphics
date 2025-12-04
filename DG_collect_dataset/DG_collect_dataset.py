# Script Name: DG_collect_dataset.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Modular Dataset Factory. Orchestrates core modules (Scrape -> Crop -> Caption -> Publish).

import sys
import os
import argparse
import importlib
from pathlib import Path

# --- 1. PATH SETUP ---
# Add 'core' to Python's search path so we can find modules
CORE_DIR = Path(__file__).parent / "core"
sys.path.append(str(CORE_DIR))

# --- 2. IMPORT UTILS & BOOTSTRAP ---
try:
    import utils 
except ImportError:
    # If running from root but core/utils.py exists
    if (CORE_DIR / "utils.py").exists():
        sys.path.append(str(CORE_DIR))
        import utils
    else:
        print(f"❌ CRITICAL: Could not find 'core/utils.py'. Check folder structure.")
        sys.exit(1)

# Auto-activate VENV and install requirements if needed
# This function MUST exist in your core/utils.py. If not, we can inline it here.
if hasattr(utils, 'bootstrap'):
    utils.bootstrap(install_reqs=True)

# --- 3. DYNAMIC MODULE LOADING ---
def load_core_module(module_name):
    try:
        return importlib.import_module(module_name)
    except ImportError as e:
        print(f"❌ Error importing 'core/{module_name}.py': {e}")
        # Fallback: try importing with core. prefix
        try:
            return importlib.import_module(f"core.{module_name}")
        except ImportError:
            sys.exit(1)

# Load the steps
mod_scrape     = load_core_module("01_setup_scrape")
mod_crop       = load_core_module("02_crop")
mod_caption    = load_core_module("03_caption")
mod_resize     = load_core_module("04_resize")
mod_downsample = load_core_module("05_downsample")
mod_publish    = load_core_module("06_publish")

# --- 4. PIPELINE ---
def run_pipeline(full_name, limit=100, gender=None, trigger=None, model=None, steps=None):
    print(f"🚀 Pipeline Started: {full_name}")
    slug = utils.slugify(full_name)

    all_steps = [1, 2, 3, 4, 5, 6]
    if steps:
        # Parse steps "1,2,5-6"
        selected_steps = []
        for s in steps:
            parts = str(s).split(',')
            for p in parts:
                if '-' in p:
                    start, end = map(int, p.split('-'))
                    selected_steps.extend(range(start, end + 1))
                else:
                    selected_steps.append(int(p))
        all_steps = selected_steps

    # Step 1: Scrape
    if 1 in all_steps:
        print("\n=== 01: SETUP & SCRAPE ===")
        # Assuming run() takes these args. Adjust if module differs.
        slug = mod_scrape.run(full_name, limit, gender)
        if not slug: return

    # Step 2: Crop
    if 2 in all_steps:
        print("\n=== 02: CROP ===")
        mod_crop.run(slug)

    # Step 3: Caption (Updated for LLM support)
    if 3 in all_steps:
        print("\n=== 03: CAPTION ===")
        # Passing trigger and model if the module supports it
        try:
            mod_caption.run(slug, trigger_word=trigger, model_name=model)
        except TypeError:
            # Fallback for older module signature
            mod_caption.run(slug)

    # Step 4: Resize
    if 4 in all_steps:
        print("\n=== 04: RESIZE MASTER ===")
        mod_resize.run(slug)

    # Step 5: Downsample
    if 5 in all_steps:
        print("\n=== 05: DOWNSAMPLE ===")
        mod_downsample.run(slug)
    
    # Step 6: Publish (Google Sheets)
    if 6 in all_steps:
        print("\n=== 06: PUBLISH ===")
        try:
            mod_publish.run(slug, trigger_word=trigger, model_name=model)
        except TypeError:
            mod_publish.run(slug)
    
    print(f"\n✅ ALL DONE: {full_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", help="Subject Full Name")
    parser.add_argument("--limit", type=int, default=50, help="Max images to scrape")
    parser.add_argument("--gender", choices=["m", "f"], help="Optional gender hint")
    parser.add_argument("--trigger", default="ohwx", help="Trigger word for captions")
    parser.add_argument("--model", choices=["moondream", "qwen"], default="moondream", help="LLM for captioning")
    parser.add_argument("--steps", nargs="*", help="Steps to run (e.g. 1 3-5)")
    
    args = parser.parse_args()

    if not args.name:
        print("Usage: python DG_collect_dataset.py 'Subject Name'")
        sys.exit(1)

    run_pipeline(args.name, args.limit, args.gender, args.trigger, args.model, args.steps)