"""
Script Name: DG_collect_dataset.py
Author: SeanF / Gemini
Date: 2025-12-06
Description: 
    Main pipeline script for collecting and processing datasets for LoRA training.
    Stages: Scrape -> Crop -> Caption -> Resize -> Downsample -> Publish.
    
    Usage: python DG_collect_dataset.py "Person Name" --trigger "ohwx" --count 15
"""

import argparse
import sys
import random
import string
import importlib
from pathlib import Path

# --- CRITICAL PATH SETUP ---
# We must add the 'core' directory to sys.path.
# This allows scripts inside 'core/' to import siblings (like utils.py)
core_path = Path.cwd() / "core"
sys.path.append(str(core_path))

def dynamic_import(module_name):
    """Helper to import modules that start with numbers"""
    try:
        # Since we added 'core' to sys.path, we can import directly
        return importlib.import_module(module_name)
    except ImportError as e:
        print(f"❌ Critical Import Error for {module_name}: {e}")
        sys.exit(1)

# --- IMPORTS ---
# Matching your ls output exactly:
mod_scrape = dynamic_import("01_setup_scrape")
mod_crop = dynamic_import("02_crop")
mod_caption = dynamic_import("03_caption")
mod_resize = dynamic_import("04_resize")      # CORRECTED: Was 04_resize_master
mod_downsample = dynamic_import("05_downsample")
mod_publish = dynamic_import("06_publish")

def generate_trigger_word(length=4):
    """Generates a random trigger word if none is provided."""
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def run_pipeline(args):
    # Create the slug (e.g. "Ed Milliband" -> "ed_milliband")
    slug = args.prompt.replace(" ", "_").lower()
    
    # Logic: Use provided trigger, or generate one if missing
    trigger_word = args.trigger if args.trigger else generate_trigger_word()
    
    print(f"🚀 Pipeline Started: {args.prompt}")
    print(f"🔑 Trigger Word: {trigger_word}")

    # --- 01: Setup & Scrape ---
    try:
        mod_scrape.run(args.prompt, args.count)
    except Exception as e:
        print(f"❌ Step 01 Failed: {e}")
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

    # --- 04: Resize Master ---
    try:
        mod_resize.run(slug)
    except Exception as e:
        print(f"❌ Step 04 Failed: {e}")
        return

    # --- 05: Downsample & Caption Injection ---
    try:
        # Passes slug and trigger word
        mod_downsample.run(slug, trigger_word)
    except Exception as e:
        print(f"❌ Step 05 Failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # --- 06: Publish ---
    try:
        # Generates the TOMLs and BAT files and moves them to /mnt/c/...
        mod_publish.run(slug, trigger_word, "wan2.1")
    except Exception as e:
        print(f"❌ Step 06 Failed: {e}")
        return

    print("\n✅ Pipeline Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dataset Collection Pipeline")
    parser.add_argument("prompt", type=str, help="Search prompt (e.g. 'Ed Milliband')")
    parser.add_argument("--trigger", type=str, help="Trigger word (optional, will generate if empty)")
    parser.add_argument("--count", type=int, default=10, help="Number of images to download")
    
    args = parser.parse_args()
    
    run_pipeline(args)