# Script Name: DG_collect_dataset.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Modular Dataset Factory. Orchestrates core modules.

import sys
import os
import argparse
import importlib
import subprocess
from pathlib import Path

# --- 1. PATH SETUP ---
CORE_DIR = Path(__file__).parent / "core"
sys.path.append(str(CORE_DIR))

# --- 2. BOOTSTRAP & UTILS ---
try:
    import utils 
except ImportError:
    print(f"❌ CRITICAL: 'core/utils.py' not found.")
    sys.exit(1)

# Auto-activate VENV
if hasattr(utils, 'bootstrap'):
    utils.bootstrap(install_reqs=True)

# --- 3. LOAD MODULES ---
def load_core_module(module_name):
    try:
        return importlib.import_module(module_name)
    except ImportError as e:
        print(f"❌ Error importing 'core/{module_name}.py': {e}")
        sys.exit(1)

mod_scrape     = load_core_module("01_setup_scrape")
mod_crop       = load_core_module("02_crop")
mod_caption    = load_core_module("03_caption")
mod_resize     = load_core_module("04_resize")
mod_downsample = load_core_module("05_downsample")
mod_publish    = load_core_module("06_publish")

# --- 4. PIPELINE ---
def run_pipeline(full_name, limit=100, gender=None, trigger=None, model=None, style=None, steps=None):
    print(f"🚀 Pipeline Started: {full_name}")
    
    slug = utils.slugify(full_name)

    all_steps = [1, 2, 3, 4, 5, 6]
    if steps:
        selected = []
        for s in steps:
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
        try: slug = mod_scrape.run(full_name, limit, gender)
        except: slug = mod_scrape.run(full_name, limit)
        if not slug: return

    # Step 2: Crop
    if 2 in all_steps:
        print("\n=== 02: CROP ===")
        mod_crop.run(slug)

    # Step 3: Caption
    if 3 in all_steps:
        print("\n=== 03: CAPTION ===")
        try: mod_caption.run(slug, trigger_word=trigger, model_name=model, style=style)
        except: mod_caption.run(slug)

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
        try: mod_publish.run(slug, trigger_word=trigger, model_name=model)
        except: mod_publish.run(slug)
    
    print(f"\n✅ ALL DONE: {full_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", help="Subject Full Name")
    parser.add_argument("--limit", type=int, default=50, help="Max images")
    parser.add_argument("--gender", choices=["m", "f"], help="Gender")
    parser.add_argument("--trigger", default="ohwx", help="Trigger word")
    parser.add_argument("--model", choices=["moondream", "qwen"], default="moondream", help="LLM Model")
    parser.add_argument("--style", default="crinklypaper", help="Caption Style")
    parser.add_argument("--skip_caption", action="store_true", help="Skip captioning")
    parser.add_argument("steps", nargs="*", help="Steps (e.g. 1 3-5)")
    
    args = parser.parse_args()

    if not args.name:
        print("Usage: DG_collect_dataset 'Subject Name' [options]")
        sys.exit(1)

    run_pipeline(args.name, args.limit, args.gender, args.trigger, args.model, args.style, args.steps)