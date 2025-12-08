import sys
import os
import subprocess
import re
import json
import random
import csv
from pathlib import Path

# --- CONFIGURATION ---
ROOT_DIR = Path(__file__).parent.parent
VENV_PATH = ROOT_DIR / ".venv"
REQUIREMENTS_PATH = ROOT_DIR / "core" / "requirements.txt"
LINUX_PROJECTS_ROOT = ROOT_DIR / "outputs"
LINUX_DATASETS_ROOT = ROOT_DIR / "datasets"
DB_PATH = ROOT_DIR / "Database" / "trigger_words.csv"

# --- CENTRAL MODEL STORE (The C: Drive Path) ---
MODEL_STORE_ROOT = Path("/mnt/c/AI/models/LLM")

# --- UNIFIED DIRECTORY SCHEMA ---
DIRS = {
    "scrape": "00_scraped",
    "crop": "01_cropped",
    "caption": "02_captions",
    "publish": "03_publish",
    "master": "03_publish/1024",
    "downsample": "03_publish",
}

# Musubi Tuner Paths
MUSUBI_PATHS = {
    'wsl_app': "/home/seanf/ai/apps/musubi-tuner",
    'wsl_models': "/home/seanf/ai/models",
    'win_app': r"C:\AI\apps\musubi-tuner",
    'win_models': r"\\wsl.localhost\Ubuntu\home\seanf\ai\models"
}

def install_package(package_name):
    print(f"📦 Installing missing dependency: {package_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"✅ Installed {package_name}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package_name}. Error: {e}")

def bootstrap(install_reqs=True):
    if not install_reqs: return
    
    # 1. TELL OLLAMA WHERE THE MODELS ARE
    os.environ['OLLAMA_MODELS'] = str(MODEL_STORE_ROOT)

    try: import deepface
    except ImportError: install_package("deepface tf-keras opencv-python")
    
    try: import playwright
    except ImportError: 
        install_package("playwright")
        print("📦 Installing Playwright browsers...")
        subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)

    try: import huggingface_hub
    except ImportError: install_package("huggingface_hub")
    
    try: from PIL import Image
    except ImportError: install_package("Pillow")
    
    try: import requests
    except ImportError: install_package("requests")

    # 2. QWEN-VL (HuggingFace) SETUP
    # Target: /mnt/c/AI/models/LLM/QWEN/qwen-vl
    from huggingface_hub import snapshot_download
    
    qwen_dir = MODEL_STORE_ROOT / "QWEN" / "qwen-vl"
    
    # Only download if not present
    if not qwen_dir.exists():
        print(f"⬇️  Downloading Qwen-VL to {qwen_dir}...")
        try:
            qwen_dir.mkdir(parents=True, exist_ok=True)
            snapshot_download(repo_id="Qwen/Qwen3-VL-4B-Instruct", local_dir=qwen_dir)
            print("✅ Qwen-VL downloaded.")
        except Exception as e:
            print(f"⚠️ Failed to download Qwen-VL: {e}")

def slugify(text):
    return re.sub(r'[\W_]+', '', text.lower()).strip('')

def gen_trigger(name):
    parts = name.split()
    first = parts[0].upper()[:2]
    last = parts[-1].upper()[0] if len(parts) > 1 else "X"
    return f"{first}{random.randint(100,999)}{last}"

def get_project_path(slug):
    return LINUX_PROJECTS_ROOT / slug

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

def update_trigger_db(slug, trigger, full_name):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = [slug, trigger, full_name]
    file_exists = DB_PATH.exists()
    
    with open(DB_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["slug", "trigger", "name"])
        writer.writerow(row)