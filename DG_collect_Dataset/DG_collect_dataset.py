import sys
import argparse
import importlib
from pathlib import Path

# --- 1. PATH SETUP ---
# Add 'core' to Python's search path so we can find 'utils.py' and the modules
CORE_DIR = Path(__file__).parent / "core"
sys.path.append(str(CORE_DIR))

# --- 2. IMPORT UTILS & BOOTSTRAP ---
try:
    import utils # Now matches core/utils.py
except ImportError as e:
    print(f"❌ CRITICAL ERROR: Could not import core/utils.py")
    print(f"Details: {e}")
    sys.exit(1)

# Auto-activate VENV and install requirements if needed
utils.bootstrap(install_reqs=True)

# --- 3. DYNAMIC MODULE LOADING ---
# We use importlib because filenames start with numbers (01_...)
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
def run_pipeline(full_name, limit=100, gender=None):
    print(f"🚀 Pipeline Started: {full_name}")
    
    # Step 1
    print("\n=== 01: SETUP & SCRAPE ===")
    slug = mod_scrape.run(full_name, limit, gender)
    if not slug: return

    # Step 2
    print("\n=== 02: CROP ===")
    mod_crop.run(slug)

    # Step 3
    print("\n=== 03: CAPTION ===")
    mod_caption.run(slug)

    # Step 4
    print("\n=== 04: RESIZE MASTER ===")
    mod_resize.run(slug)

    # Step 5
    print("\n=== 05: DOWNSAMPLE ===")
    mod_downsample.run(slug)
    
    # Step 6
    print("\n=== 06: PUBLISH ===")
    mod_publish.run(slug)
    
    print(f"\n✅ ALL DONE: {full_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", help="Subject Full Name")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--gender", choices=["m", "f"])
    parser.add_argument("--only-step", type=int, help="Run specific step (1-6)")
    args = parser.parse_args()

    if not args.name:
        print("Usage: python DG_collect_dataset.py 'Subject Name'")
        sys.exit(1)

    if args.only_step:
        slug = utils.slugify(args.name)
        steps = {
            1: lambda: mod_scrape.run(args.name, args.limit, args.gender),
            2: lambda: mod_crop.run(slug),
            3: lambda: mod_caption.run(slug),
            4: lambda: mod_resize.run(slug),
            5: lambda: mod_downsample.run(slug),
            6: lambda: mod_publish.run(slug)
        }
        if args.only_step in steps:
            steps[args.only_step]()
        else:
            print("❌ Invalid step number. Use 1-6.")
    else:
        run_pipeline(args.name, args.limit, args.gender)