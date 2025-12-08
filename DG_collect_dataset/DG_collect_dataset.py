import sys
import argparse
import importlib
from pathlib import Path

CORE_DIR = Path(__file__).parent / "core"
sys.path.append(str(CORE_DIR))

try: import utils
except ImportError: sys.exit(1)

utils.bootstrap(install_reqs=True)

def load_core_module(name):
    return importlib.import_module(name)

mod_scrape = load_core_module("01_setup_scrape")
mod_crop = load_core_module("02_crop")
mod_caption = load_core_module("03_caption")
mod_publish = load_core_module("04_publish")

def run_pipeline(full_name, limit=100, gender=None, model="moondream", trigger=None):
    print(f"🚀 Pipeline Started: {full_name}")
    slug = mod_scrape.run(full_name, limit, gender, trigger)
    if not slug: return
    mod_crop.run(slug)
    mod_caption.run(slug, model=model)
    mod_publish.run(slug)
    print(f"\n✅ ALL DONE: {full_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--count", type=int) 
    parser.add_argument("--gender", choices=["m", "f"])
    parser.add_argument("--trigger", type=str)
    parser.add_argument("--only-step", type=int)
    parser.add_argument("--model", default="moondream")
    
    args = parser.parse_args()
    if not args.name: sys.exit(1)
    limit = args.count if args.count else args.limit

    if args.only_step:
        slug = utils.slugify(args.name)
        if args.only_step == 1: mod_scrape.run(args.name, limit, args.gender, args.trigger)
        elif args.only_step == 2: mod_crop.run(slug)
        elif args.only_step == 3: mod_caption.run(slug, model=args.model)
        elif args.only_step == 4: mod_publish.run(slug)
    else:
        run_pipeline(args.name, limit, args.gender, args.model, args.trigger)