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

# --- 2. BOOTSTRAP ---
def check_main_dependencies():
    """Installs ONLY what this main script needs."""
    required = ['requests', 'tqdm']
    missing = []
    for pkg in required:
        try: __import__(pkg)
        except ImportError: missing.append(pkg)
    
    if missing:
        print(f"--> Installing main deps: {', '.join(missing)}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)

check_main_dependencies()

# --- 3. DYNAMIC MODULE LOADING ---
def load_core_module(module_name):
    try:
        return importlib.import_module(module_name)
    except ImportError as e:
        print(f"❌ Error importing 'core/{module_name}.py': {e}")
        sys.exit(1)

try:
    import utils 
except ImportError:
    # If running from root but core/utils.py exists
    if (CORE_DIR / "utils.py").exists():
        sys.path.append(str(CORE_DIR))
        import utils
    else:
        print(f"❌ CRITICAL: Could not find 'core/utils.py'. Check folder structure.")
        sys.exit(1)

# Auto-activate VENV and install requirements if needed
if hasattr(utils, 'bootstrap'):
    utils.bootstrap(install_reqs=True)

# Load Steps
mod_scrape     = load_core_module("01_setup