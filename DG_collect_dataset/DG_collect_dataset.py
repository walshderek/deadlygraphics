import sys
import argparse
import importlib
from pathlib import Path

# Setup Core Path
CORE_DIR = Path(__file__).parent / "core"
sys.path.append(str(CORE_DIR))

try:
    import utils
except ImportError as e:
    print(f"❌ Critical Error: Could not import 'utils' from {CORE_DIR}.")
    sys.exit(1)

# Ensure environment is bootstrapped (install reqs)
utils.bootstrap(install_reqs=True)

def load_core_module(name):
    try:
        return importlib.import_module(name)
    except ImportError as e:
        print(f"❌ Critical Import Error for {name}: {e}")
        sys.exit(1)

# Load Modules
mod_scrape = load_core_module("01_setup_scrape")
mod_crop = load_core_module("02_crop")
mod_caption = load_core_module("03_caption")
mod_publish = load_core_module("04_publish")

def run_pipeline(full_name, limit=100, gender=None, model="moondream"):
    print(f"🚀 Pipeline Started: {full_name}")
    
    # Step 1: Scrape
    slug = mod_scrape.run(full_name, limit, gender)
    if not slug:
        return

    # Step 2: Crop
    mod_crop.run(slug)

    # Step 3: Caption
    mod_caption.run(slug, model=model)

    # Step 4: Publish
    mod_publish.run(slug)

    print(f"\n✅ ALL DONE: {full_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", help="Subject Full Name")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--gender", choices=["m", "f"])
    parser.add_argument("--only-step", type=int, help="Run specific step (1-4)")
    parser.add_argument("--model", default="moondream", choices=["moondream", "qwen-vl"], help="Caption model")
    
    args = parser.parse_args()

    if not args.name:
        parser.print_help()
        sys.exit(1)

    if args.only_step:
        slug = utils.slugify(args.name)
        steps = {
            1: mod_scrape,
            2: mod_crop,
            3: mod_caption,
            4: mod_publish
        }
        if args.only_step in steps:
            print(f"🚀 Running Step {args.only_step} for {slug}...")
            if args.only_step == 1:
                steps[1].run(args.name, args.limit, args.gender)
            elif args.only_step == 3:
                steps[3].run(slug, model=args.model)
            else:
                steps[args.only_step].run(slug)
        else:
            print("❌ Invalid step number. Use 1-4.")
    else:
        run_pipeline(args.name, args.limit, args.gender, args.model)