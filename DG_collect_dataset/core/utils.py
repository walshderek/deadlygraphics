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
DB_PATH = ROOT_DIR / "Database" / "trigger_words.csv"

# --- UNIFIED DIRECTORY SCHEMA ---
DIRS = {
    "scrape": "00_scraped",
    "crop": "01_cropped",
    "caption": "02_captions",
    "clean": "03_cleaned",
    "qc": "04_qc",
    "publish": "05_publish",
    "master": "05_publish/1024",
    "downsample": "05_publish",
}

# Musubi Tuner Paths
MUSUBI_PATHS = {
    'wsl_app': "/home/seanf/ai/apps/musubi-tuner",
    'wsl_models': "/home/seanf/ai/models",
    'win_app': r"C:\AI\apps\musubi-tuner",
    'win_models': r"\\wsl.localhost\Ubuntu\home\seanf\ai\models"
}

# Central Model Store
MODEL_STORE_ROOT = Path("/mnt/c/AI/models/LLM")

def install_package(package_name):
    print(f"📦 Installing missing dependency: {package_name}...")
    try:
        pkgs = package_name.split()
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + pkgs)
        print(f"✅ Installed {package_name}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package_name}. Error: {e}")

def bootstrap(install_reqs=True):
    if not install_reqs: return
    
    os.environ['OLLAMA_MODELS'] = str(MODEL_STORE_ROOT)

    # Core Deps
    try: import deepface
    except ImportError: install_package("deepface tf-keras opencv-python")
    try: import playwright
    except ImportError: 
        install_package("playwright")
        subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
    try: import huggingface_hub
    except ImportError: install_package("huggingface_hub")
    try: import requests
    except ImportError: install_package("requests")
    
    # Qwen/Advanced Deps
    # Added qwen-vl-utils and accelerate for Qwen2.5-VL
    try: import qwen_vl_utils
    except ImportError: install_package("qwen-vl-utils accelerate transformers torch torchvision")
    try: import sklearn
    except ImportError: install_package("scikit-learn")

    # Qwen-VL Download (Qwen2.5-VL-3B-Instruct)
    from huggingface_hub import snapshot_download
    # Store in QWEN/Qwen2.5-VL-3B-Instruct
    qwen_dir = MODEL_STORE_ROOT / "QWEN" / "Qwen2.5-VL-3B-Instruct"
    if not qwen_dir.exists():
        try:
            print(f"⬇️  Downloading Qwen2.5-VL to {qwen_dir}...")
            qwen_dir.mkdir(parents=True, exist_ok=True)
            snapshot_download(repo_id="Qwen/Qwen2.5-VL-3B-Instruct", local_dir=qwen_dir)
            print("✅ Qwen-VL downloaded.")
        except Exception as e:
            print(f"⚠️ Failed to download Qwen-VL: {e}")

def slugify(text):
    return re.sub(r'[\W]+', '_', text.lower()).strip('_')

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
        if not file_exists: writer.writerow(["slug", "trigger", "name"])
        writer.writerow(row)