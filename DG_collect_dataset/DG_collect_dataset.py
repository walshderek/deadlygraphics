# Script Name: DG_collect_dataset.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Modular Dataset Factory. Orchestrates core modules (Scrape -> Crop -> Caption -> Publish).

import sys
import os
import argparse
import importlib
import subprocess
from pathlib import Path

# --- 1. PATH SETUP ---
# Add 'core' to Python's search path so we can find 'utils.py' and the modules
CORE_DIR = Path(__file__).parent / "core"
sys.path.append(str(CORE_DIR))

# --- 2. IMPORT UTILS & BOOTSTRAP ---
try:
    import utils 
except ImportError:
    print(f"❌ CRITICAL ERROR: Could not import core/utils.py")
    sys.exit(1)

# Auto-activate VENV and install requirements if needed
if hasattr(utils, 'bootstrap'):
    utils.bootstrap(install_reqs=True)

# --- 3. DYNAMIC MODULE LOADING ---
def load_core_module(module_name):
    try:
        return importlib.import_module(module_name)
    except ImportError as e:
        print(f"❌ Error importing 'core/{module_name}.py': {e}")
        sys.exit(1)

# Load the steps
mod_scrape     = load_core_module("01_setup_scrape")
mod_crop       = load_core_module("02_crop")
mod_caption    = load_core_module("03_caption")
mod_resize     = load_core_module("04_resize")
mod_downsample = load_core_module("05_downsample")
mod_publish    = load_core_module("06_publish")

# --- 4. PIPELINE ---
def run_pipeline(full_name, limit=100, gender=None, trigger=None, model=None, style=None, steps=None):
    print(f"🚀 Pipeline Started: {full_name}")
    
    # Slugify name for folder usage
    slug = utils.slugify(full_name)

    # Determine which steps to run
    all_steps = [1, 2, 3, 4, 5, 6]
    if steps:
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
        # Scrape module usually takes (name, limit, gender)
        # We check if it returns a slug, or if we need to rely on the calculated one
        res = mod_scrape.run(full_name, limit, gender)
        if res: slug = res # Update slug if scrape module refined it

    # Step 2: Crop
    if 2 in all_steps:
        print("\n=== 02: CROP ===")
        mod_crop.run(slug)

    # Step 3: Caption (LLM)
    if 3 in all_steps:
        print("\n=== 03: CAPTION ===")
        try:
            # Pass new LLM args if module supports them
            mod_caption.run(slug, trigger_word=trigger, model_name=model, style=style)
        except TypeError:
            print("⚠️ Module 03_caption doesn't support new args. Running default.")
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
            # Pass trigger for logging
            mod_publish.run(slug, trigger_word=trigger, model_name=model)
        except TypeError:
            print("⚠️ Module 06_publish doesn't support new args. Running default.")
            mod_publish.run(slug)
    
    print(f"\n✅ ALL DONE: {full_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", help="Subject Full Name")
    parser.add_argument("--limit", type=int, default=50, help="Max images")
    parser.add_argument("--gender", choices=["m", "f"], help="Gender (optional)")
    parser.add_argument("--trigger", default="ohwx", help="Trigger word")
    parser.add_argument("--model", choices=["moondream", "qwen"], default="moondream", help="LLM Model")
    parser.add_argument("--style", default="crinklypaper", help="Caption Style")
    parser.add_argument("--steps", nargs="*", help="Steps to run (e.g. 1 3-5)")
    
    args = parser.parse_args()

    if not args.name:
        print("Usage: DG_collect_dataset 'Subject Name' [options]")
        sys.exit(1)

    run_pipeline(args.name, args.limit, args.gender, args.trigger, args.model, args.style, args.steps)