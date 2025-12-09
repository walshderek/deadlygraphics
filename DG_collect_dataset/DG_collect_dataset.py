import argparse
import sys
import os
import importlib
import time

# --- FIX: Add 'core' to path so we can import utils ---
current_dir = os.path.dirname(os.path.abspath(__file__))
core_dir = os.path.join(current_dir, "core")
if core_dir not in sys.path:
    sys.path.append(core_dir)

import utils

# MAPPING: Step Number -> Module Name
STEPS = {
    1: "01_setup_scrape",
    2: "02_crop",
    3: "03_validate",   
    4: "04_clean",      
    5: "05_caption",    
    6: "06_publish"     
}

def run_pipeline(slug, limit, count, gender, trigger, model, only_step=None):
    print(f"🚀 Pipeline Started: {slug}")
    print(f"🔑 Trigger Word: {trigger}")
    
    # Save config first
    utils.save_config(slug, {
        'trigger': trigger,
        'gender': gender,
        'limit': limit,
        'count': count,
        'model': model
    })

    # Determine which steps to run
    if only_step:
        try:
            step_nums = [int(only_step)]
        except ValueError:
            print(f"❌ Error: --only-step must be a number (1-6).")
            return
    else:
        step_nums = sorted(STEPS.keys())

    # Execute Steps
    for step_num in step_nums:
        module_name = STEPS.get(step_num)
        if not module_name:
            print(f"⚠️ Warning: Step {step_num} is not defined.")
            continue

        print(f"\n--> [{module_name}] Running Step {step_num}...")
        
        try:
            # Dynamic Import
            module = importlib.import_module(module_name)
            
            # Run the module
            if hasattr(module, 'run'):
                module.run(slug)
            else:
                print(f"❌ Error: {module_name} does not have a 'run(slug)' function.")
                
        except ImportError as e:
            print(f"❌ Error: Could not load script '{module_name}'. Details: {e}")
        except Exception as e:
            print(f"❌ Error during {module_name}: {e}")
            import traceback
            traceback.print_exc()
            return 

    print(f"\n✅ Pipeline Complete for {slug}")

def main():
    parser = argparse.ArgumentParser(description="DeadlyGraphics Dataset Pipeline")
    parser.add_argument("name", help="Name of the person (e.g. 'Ed Milliband')")
    parser.add_argument("--limit", type=int, default=100, help="Max images to scrape")
    parser.add_argument("--count", type=int, default=100, help="Target count")
    parser.add_argument("--gender", choices=['m', 'f'], default='m', help="Gender")
    parser.add_argument("--trigger", default="ohwx", help="Trigger word")
    parser.add_argument("--only-step", help="Run only a specific step number (1-6)")
    parser.add_argument("--model", default="qwen-vl", help="Model for captioning")

    args = parser.parse_args()
    run_pipeline(args.name, args.limit, args.count, args.gender, args.trigger, args.model, args.only_step)

if __name__ == "__main__":
    main()