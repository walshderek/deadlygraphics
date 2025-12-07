import argparse
import sys
import importlib
from pathlib import Path

# Setup Core Path
core_path = Path.cwd() / "core"
sys.path.append(str(core_path))

try: import utils
except ImportError: sys.exit(1)

# Bootstrap (Install Qwen, Ollama, etc)
utils.bootstrap(install_reqs=True)

def dynamic_import(name):
    return importlib.import_module(name)

# Imports
mod_scrape = dynamic_import("01_setup_scrape")
mod_crop = dynamic_import("02_crop")
mod_caption = dynamic_import("03_caption")
mod_publish = dynamic_import("04_publish")

def run_pipeline(args):
    # 1. Slugify (Standard)
    slug = utils.slugify(args.prompt)
    print(f"🚀 Pipeline: {args.prompt} -> {slug}")

    # 2. Scrape (Generates trigger if needed)
    mod_scrape.run(args.prompt, args.count, slug, args.trigger)
    
    # 3. Crop
    mod_crop.run(slug)
    
    # 4. Caption (Supports optional Qwen model)
    mod_caption.run(slug, model_type=args.model)
    
    # 5. Publish (Resize, Downsample, Configs)
    mod_publish.run(slug)

    print("\n✅ Pipeline Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", type=str)
    parser.add_argument("--trigger", type=str, help="Optional trigger (defaults to random)")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--model", default="moondream", choices=["moondream", "qwen-vl"], help="Caption model")
    
    args = parser.parse_args()
    run_pipeline(args)