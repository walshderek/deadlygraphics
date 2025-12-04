import sys
import os
import subprocess
import re
import json
import random
import csv
from pathlib import Path

# --- PATH CONFIGURATION ---
ROOT_DIR = Path(__file__).parent.parent 
VENV_PATH = ROOT_DIR / ".venv"
REQUIREMENTS_PATH = ROOT_DIR / "core" / "requirements.txt"

# Output Directories
LINUX_PROJECTS_ROOT = ROOT_DIR / "outputs" 
LINUX_DATASETS_ROOT = ROOT_DIR / "datasets" 
DB_PATH = ROOT_DIR / "Database" / "trigger_words.csv"

DIRS = {
    "scrape": "00_scraped",
    "crop": "01_cropped",
    "caption": "02_captions",
    "master": "03_master_1024",
    "downsample": "04_downsampled",
    "publish": "05_publish"
}

# --- MUSUBI CONFIG ---
MUSUBI_PATHS = {
    "win_models": r"C:\AI\models",
    "wsl_models": "/home/seanf/ai/models",
    "win_app": r"C:\AI\apps\musubi-tuner",
    "wsl_app": "/home/seanf/ai/apps/musubi-tuner"
}

# --- PATH HELPERS ---
def get_windows_unc_path(linux_path):
    r"""
    Converts /home/seanf/ai/... -> \\wsl.localhost\Ubuntu\home\seanf\ai\...
    """
    p = str(linux_path).replace("/mnt/c/", "C:/")
    if p.startswith("/home"):
        win_style = p.replace("/", "\\")
        return f"\\\\wsl.localhost\\Ubuntu{win_style}"
    return p

# --- DATABASE HELPERS ---
def update_trigger_db(name, trigger, gender):
    """Updates the CSV database with the new character."""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    file_exists = DB_PATH.exists()
    
    # Read existing to avoid duplicates
    rows = []
    if file_exists:
        with open(DB_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    
    # Check if trigger already exists
    for row in rows:
        if row['TriggerWord'] == trigger:
            return # Already exists
            
    # Add new row
    with open(DB_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Name", "TriggerWord", "Gender"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({"Name": name, "TriggerWord": trigger, "Gender": gender})
    
    print(f"📚 Database updated: {name} -> {trigger}")

# --- BOOTSTRAPPER ---
def bootstrap(install_reqs=False):
    if sys.platform == "win32":
        venv_python = VENV_PATH / "Scripts" / "python.exe"
    else:
        venv_python = VENV_PATH / "bin" / "python3"

    is_venv = (str(VENV_PATH.resolve()) in sys.executable) or (sys.prefix != sys.base_prefix)

    if not is_venv:
        if not venv_python.exists():
            print(f"❌ VENV missing at {VENV_PATH}")
            print("   Run: python3 -m venv .venv")
            sys.exit(1)
        
        try:
            subprocess.check_call([str(venv_python)] + sys.argv)
            sys.exit(0)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)

    if install_reqs and REQUIREMENTS_PATH.exists():
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH), "-q"]
            )
        except Exception:
            pass

# --- PROJECT UTILS ---
def get_project_path(project_slug):
    return LINUX_PROJECTS_ROOT / project_slug

def load_config(project_slug):
    path = get_project_path(project_slug) / "project_config.json"
    if not path.exists(): return None
    with open(path, 'r') as f: return json.load(f)

def save_config(project_slug, data):
    path = get_project_path(project_slug) / "project_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f: json.dump(data, f, indent=4)

def slugify(text):
    return re.sub(r'[\W_]+', '_', text.lower()).strip('_')

def gen_trigger(name):
    parts = name.split()
    first = parts[0].upper()[:2]
    last = parts[-1].upper()[0] if len(parts) > 1 else "X"
    return f"{first}{random.randint(100,999)}{last}"