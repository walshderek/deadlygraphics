import sys
import os
import subprocess
import re
import json
import random
import csv
from pathlib import Path

# --- CONFIGURATION ---
# Since this file is in /core/, parent is root, parent.parent is outside the project
# logic: utils.py is in /core/. 
# Path(__file__).parent is /core/
# Path(__file__).parent.parent is /DG_collect_dataset/ (ROOT)
ROOT_DIR = Path(__file__).parent.parent 
VENV_PATH = ROOT_DIR / ".venv"
REQUIREMENTS_PATH = ROOT_DIR / "core" / "requirements.txt"
LINUX_PROJECTS_ROOT = ROOT_DIR / "outputs"
LINUX_DATASETS_ROOT = ROOT_DIR / "datasets"
DB_PATH = ROOT_DIR / "Database" / "trigger_words.csv"

# --- UNIFIED DIRECTORY SCHEMA (1-6 PIPELINE) ---
DIRS = {
    "scrape": "01_scrape",
    "crop": "02_crop",
    "validate": "03_validate",
    "clean": "04_clean",
    "caption": "05_caption",
    "publish": "06_publish",
    "master": "06_publish/1024",
    "downsample": "06_publish",
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
    try: import diffusers
    except ImportError: install_package("diffusers transformers accelerate scipy")
    try: import sklearn
    except ImportError: install_package("scikit-learn")
    try: import qwen_vl_utils
    except ImportError: install_package("qwen-vl-utils")
    try: import bitsandbytes
    except ImportError: install_package("bitsandbytes")
    try: import accelerate
    except ImportError: install_package("accelerate")
    from huggingface_hub import snapshot_download
    qwen_dir = MODEL_STORE_ROOT / "QWEN" / "Qwen2.5-VL-3B-Instruct"
    if not qwen_dir.exists():
        try:
            qwen_dir.mkdir(parents=True, exist_ok=True)
            snapshot_download(repo_id="Qwen/Qwen2.5-VL-3B-Instruct", local_dir=qwen_dir)
        except: pass

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

# --- THE FIX IS HERE ---
def save_config(slug, data):
    path = get_project_path(slug) / "project_config.json"
    # Ensure the directory exists before writing!
    path.parent.mkdir(parents=True, exist_ok=True)
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