import os
import json
import sys
import subprocess
import shutil
from pathlib import Path

# --- CONFIGURATION ---
BASE_PATH = Path(os.getcwd())
VENV_PATH = BASE_PATH / ".venv"

# Directory Structure Map
DIRS = {
    'scraped': '00_scraped',
    'crop': '01_cropped',
    'caption': '02_captions',
    'master': '03_master_1024',
    'resize': '04_resize',
    'downsample': '05_downsample',
    'publish': '06_publish'
}

# Musubi Tuner Paths (Dual OS Support)
MUSUBI_PATHS = {
    'wsl_app': "/home/seanf/ai/apps/musubi-tuner",
    'wsl_models': "/home/seanf/ai/models",
    'win_app': r"C:\AI\apps\musubi-tuner",
    'win_models': r"\\wsl.localhost\Ubuntu\home\seanf\ai\models"
}

# --- MODEL PATH CONFIGURATION ---
# Map C:\AI\models\LLM to WSL path
OLLAMA_MODELS_WIN = r"C:\AI\models\LLM"
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
    
    # 1. Set Ollama Model Path
    os.environ['OLLAMA_MODELS'] = OLLAMA_MODELS_WSL
    
    if not install_reqs:
        return

    # 2. Check and Install Critical Libraries
    # Ollama
    try:
        import ollama
    except ImportError:
        install_package("ollama")

    # Slugify
    try:
        from slugify import slugify
    except ImportError:
        install_package("python-slugify")
        
    # Pillow (Required for core modules)
    try:
        from PIL import Image
    except ImportError:
        install_package("Pillow")

    # Requests (Used by scrape)
    try:
        import requests
    except ImportError:
        install_package("requests")

def slugify(text):
    """Wraps python-slugify. Ensures it's imported after bootstrap."""
    try:
        from slugify import slugify as _slugify
        return _slugify(text)
    except ImportError:
        print("❌ Error: python-slugify not installed. Bootstrap failed.")
        sys.exit(1)

def get_project_path(slug):
    return BASE_PATH / "outputs" / slug

def load_config(slug):
    path = get_project_path(slug) / "project_config.json"
    if not path.exists():
        return None
    with open(path, 'r') as f:
        return json.load(f)

def save_config(slug, data):
    path = get_project_path(slug) / "project_config.json"
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def get_windows_unc_path(wsl_path):
    """Converts a WSL path (/home/seanf/...) to Windows UNC"""
    if not wsl_path.startswith("/home"):
        return wsl_path 
    
    clean_path = str(wsl_path).replace("/", "\\")
    if clean_path.startswith("\\"):
        clean_path = clean_path[1:]
        
    return f"\\\\wsl.localhost\\Ubuntu\\{clean_path}"