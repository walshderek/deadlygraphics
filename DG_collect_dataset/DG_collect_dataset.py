"""
Script Name: DG_collect_dataset.py
Author: DeadlyGraphics
Description: Main pipeline script.
"""
import argparse
import sys
import os
import importlib
from pathlib import Path

# --- CRITICAL PATH SETUP ---
core_path = Path.cwd() / "core"
sys.path.append(str(core_path))

try:
    import utils
except ImportError as e:
    print(f"❌ Critical Error: Could not import 'utils' from {core_path}.")
    print(f"   Details: {e}")
    sys.exit(1)

# --- BOOTSTRAP DEPENDENCIES ---
# This must happen BEFORE importing core modules that rely on them
utils.bootstrap(install_reqs=True)

# Dynamic Import Helper
def dynamic_import(module_name):
    try:
        return importlib.import_module(module_name)
    except ImportError as e:
        print(f"❌ Critical Import Error for {module_name}: {e}")
        sys.exit(1)

# --- IMPORTS ---
mod_scrape = dynamic_import("01_setup_scrape")
mod_crop = dynamic_import("02_crop")
mod_caption = dynamic_import("03_caption")
mod_resize = dynamic_import("04_resize")
mod_downsample = dynamic_import("05_downsample")
mod_publish = dynamic_import("06_publish")

def run_pipeline(args):
    # Determine slug using the utils function (which is now safe to use)
    slug = utils.slugify(args.prompt)
    
    trigger = args.trigger if args.trigger else slug[:4]
    
    print(f"🚀 Pipeline Started: {args.prompt}")
    print(f"🔑 Trigger: {trigger}")
    
    config = {
        'prompt': args.prompt,
        'trigger': trigger,
        'count': args.count
    }
    
    # Ensure project folder exists before saving config
    (utils.BASE_PATH / "outputs" / slug).mkdir(parents=True, exist_ok=True)
    utils.save_config(slug, config)

    # --- 01: Scrape ---
    try:
        mod_scrape.run(args.prompt, args.count, slug)
    except Exception as e:
        print(f"❌ Step 01 Failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # --- 02: Crop ---
    try:
        mod_crop.run(slug)
    except Exception as e:
        print(f"❌ Step 02 Failed: {e}")
        return

    # --- 03: Caption ---
    try:
        mod_caption.run(slug)
    except Exception as e:
        print(f"❌ Step 03 Failed: {e}")
        return

    # --- 04: Resize (Master) ---
    try:
        mod_resize.run(slug)
    except Exception as e:
        print(f"❌ Step 04 Failed: {e}")
        return

    # --- 05: Downsample ---
    try:
        mod_downsample.run(slug)
    except Exception as e:
        print(f"❌ Step 05 Failed: {e}")
        return

    # --- 06: Publish ---
    try:
        mod_publish.run(slug)
    except Exception as e:
        print(f"❌ Step 06 Failed: {e}")
        return

    print("\n✅ Pipeline Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dataset Collection Pipeline")
    parser.add_argument("prompt", type=str, help="Search prompt (e.g. 'Ed Milliband')")
    parser.add_argument("--trigger", type=str, help="Trigger word")
    parser.add_argument("--count", type=int, default=10, help="Number of images to download")
    
    args = parser.parse_args()
    run_pipeline(args)