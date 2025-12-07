import os
import json
import sys
import subprocess
import random
import re
from pathlib import Path

# --- CONFIGURATION ---
BASE_PATH = Path(os.getcwd())
VENV_PATH = BASE_PATH / ".venv"

# Directory Structure Map
# Merged resize/downsample/publish into '03_publish'
DIRS = {
    'scraped': '00_scraped',
    'crop': '01_cropped',
    'caption': '02_captions',
    'publish': '03_publish' 
}

# Musubi Tuner Paths (Dual OS Support)
MUSUBI_PATHS = {
    'wsl_app': "/home/seanf/ai/apps/musubi-tuner",
    'wsl_models': "/home/seanf/ai/models",
    'win_app': r"C:\AI\apps\musubi-tuner",
    'win_models': r"\\wsl.localhost\Ubuntu\home\seanf\ai\models"
}

# --- MODEL PATH CONFIGURATION ---
OLLAMA_MODELS_WSL = "/mnt/c/AI/models/LLM"

def install_package(package_name):
    """Installs a package via pip."""
    print(f"📦 Installing missing dependency: {package_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"✅ Installed {package_name}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package_name}. Error: {e}")
        sys.exit(1)

def bootstrap(install_reqs=True):
    """Ensures environment variables and dependencies are set up."""
    os.environ['OLLAMA_MODELS'] = OLLAMA_MODELS_WSL
    
    if not install_reqs: return

    # Core deps
    try: import ollama
    except ImportError: install_package("ollama")

    try: from PIL import Image
    except ImportError: install_package("Pillow")

    try: import requests
    except ImportError: install_package("requests")
    
    # Qwen-VL Deps (Always download/check, even if not used by default)
    try: import torch
    except ImportError: install_package("torch torchvision torchaudio")
    
    try: import transformers
    except ImportError: install_package("transformers")
    
    try: import huggingface_hub
    except ImportError: install_package("huggingface_hub")

    # Download Qwen-VL Model
    from huggingface_hub import snapshot_download
    models_dir = BASE_PATH / "models"
    models_dir.mkdir(exist_ok=True)
    qwen_path = models_dir / "qwen-vl"
    
    if not qwen_path.exists():
        print("⬇️  Downloading qwen-vl model (This runs once)...")
        try:
            snapshot_download(repo_id="Salesforce/Qwen-VL-Chat", local_dir=qwen_path)
            print("✅ Qwen-VL downloaded.")
        except Exception as e:
            print(f"⚠️ Failed to download Qwen-VL: {e}")

def slugify(text):
    """Standard slugify: 'Ed Milliband' -> 'ed_milliband'"""
    # Remove non-word chars (allow spaces/hyphens first)
    text = re.sub(r'[^\w\s-]', '', text).lower()
    # Replace spaces/hyphens with underscore
    return re.sub(r'[-\s]+', '_', text).strip('-_')

def gen_trigger(name):
    """Generates trigger: First 2 letters (Upper) + Random 100-999 + Last Initial"""
    parts = name.split()
    first = parts[0].upper()[:2]
    last = parts[-1].upper()[0] if len(parts) > 1 else "X"
    return f"{first}{random.randint(100,999)}{last}"

def get_project_path(slug):
    return BASE_PATH / "outputs" / slug

def load_config(slug):
    path = get_project_path(slug) / "project_config.json"
    if not path.exists(): return None
    with open(path, 'r') as f: return json.load(f)

def save_config(slug, data):
    path = get_project_path(slug) / "project_config.json"
    with open(path, 'w') as f: json.dump(data, f, indent=4)

def get_windows_unc_path(wsl_path):
    if not wsl_path.startswith("/home"): return wsl_path 
    clean_path = str(wsl_path).replace("/", "\\")
    if clean_path.startswith("\\"): clean_path = clean_path[1:]
    return f"\\\\wsl.localhost\\Ubuntu\\{clean_path}"