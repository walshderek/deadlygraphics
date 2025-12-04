# Script Name: DG_collect_dataset.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Modular Orchestrator. Calls core modules for Scrape -> Crop -> Caption -> Publish.

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
    print(f"❌ Critical: 'core/utils.py' not found. Check folder structure.")
    sys.exit(1)

# Self-Healing: Check if main dependencies exist
def check_orchestrator_deps():
    try:
        import requests
        import tqdm
    except ImportError:
        print("--> Installing orchestrator deps (requests, tqdm)...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests', 'tqdm'])

check_orchestrator_deps()

# --- 3. MODULE LOADER ---
def load_module(name):
    try:
        return importlib.import_module(name)
    except ImportError as e:
        print(f"❌ Failed to load module '{name}': {e}")
        sys.exit(1)

mod_scrape     = load_module("01_setup_scrape")
mod_crop       = load_module("02_crop")
mod_caption    = load_module("03_caption")
mod_resize     = load_module("04_resize")
mod_downsample = load_module("05_downsample")
mod_publish    = load_module("06_publish")

# --- 4. PIPELINE ---
def run_pipeline(args):
    print(f"🚀 Pipeline Started: {args.name}")
    
    # Generate slug (folder name)
    slug = utils.slugify(args.name)
    
    # Determine steps
    all_steps = [1, 2, 3, 4, 5, 6]
    if args.steps:
        selected = []
        for s in args.steps:
            parts = s.split(',')
            for p in parts:
                if '-' in p:
                    start, end = map(int, p.split('-'))
                    selected.extend(range(start, end + 1))
                else:
                    selected.append(int(p))
        all_steps = selected

    # --- STEP 1: SCRAPE ---
    if 1 in all_steps:
        print("\n=== 01: SETUP & SCRAPE (Bing) ===")
        try:
            mod_scrape.run(args.name, args.count)
        except Exception as e:
            print(f"❌ Scrape failed: {e}")
            return

    # --- STEP 2: CROP ---
    if 2 in all_steps:
        print("\n=== 02: CROP (Face Detection) ===")
        mod_crop.run(slug)

    # --- STEP 3: CAPTION ---
    if 3 in all_steps:
        if args.skip_caption:
            print("\n=== 03: CAPTION (Skipped by user) ===")
        else:
            print(f"\n=== 03: CAPTION ({args.model} / {args.style}) ===")
            mod_caption.run(slug, trigger=args.trigger, model=args.model, style=args.style)

    # --- STEP 4: RESIZE ---
    if 4 in all_steps:
        print("\n=== 04: RESIZE MASTER ===")
        mod_resize.run(slug)

    # --- STEP 5: DOWNSAMPLE ---
    if 5 in all_steps:
        print("\n=== 05: DOWNSAMPLE ===")
        mod_downsample.run(slug)

    # --- STEP 6: PUBLISH ---
    if 6 in all_steps:
        print("\n=== 06: PUBLISH (Log & Config) ===")
        mod_publish.run(slug, trigger=args.trigger, model=args.model)

    print(f"\n✅ ALL DONE: {args.name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", help="Subject Name (Search Term)")
    parser.add_argument("--count", type=int, default=50, help="Max images to scrape")
    parser.add_argument("--trigger", default="ohwx", help="Trigger word for captioning")
    parser.add_argument("--model", choices=["moondream", "qwen"], default="moondream", help="LLM to use")
    parser.add_argument("--style", choices=["dg_char", "crinklypaper"], default="crinklypaper", help="Caption style")
    parser.add_argument("--skip_caption", action="store_true", help="Skip captioning step")
    parser.add_argument("steps", nargs="*", help="Specific steps to run (e.g. 1 3-5)")
    
    args = parser.parse_args()

    if not args.name:
        print("Usage: DG_collect_dataset 'Subject Name' [options]")
        sys.exit(1)

    run_pipeline(args)