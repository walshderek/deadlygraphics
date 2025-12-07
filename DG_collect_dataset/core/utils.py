# Script Name: core/utils.py
# Authors: DeadlyGraphics, Gemini
# Description: Shared utilities, paths, database logging, and dependency management.

import sys
import os
import subprocess
import re
import json
import random
import csv
from pathlib import Path

# --- PATH CONFIGURATION ---
# We assume we are running inside 'ai/apps/DG_collect_dataset'
ROOT_DIR = Path(__file__).parent.parent 
VENV_PATH = ROOT_DIR / "venv"
REQUIREMENTS_PATH = ROOT_DIR / "core" / "requirements.txt"

# Output Directories
# Adjust these relative to your workspace root if needed
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

# --- MUSUBI CONFIG (Restored from your upload) ---
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
        # Assuming standard WSL Ubuntu distro name. Adjust if using Debian/etc.
        win_style = p.replace("/", "\\")
        return f"\\\\wsl.localhost\\Ubuntu{win_style}"
    return p

# --- DATABASE HELPERS ---
def update_trigger_db(name, trigger, gender):
    """Updates the CSV database with the new character."""
    if not DB_PATH.parent.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    file_exists = DB_PATH.exists()
    rows = []
    
    if file_exists:
        with open(DB_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    
    # Check for duplicate
    for row in rows:
        if row.get('TriggerWord') == trigger:
            print(f"   [DB] Trigger '{trigger}' already exists.")
            return
            
    # Append
    with open(DB_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Name", "TriggerWord", "Gender"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({"Name": name, "TriggerWord": trigger, "Gender": gender})
    
    print(f"📚 Database updated: {name} -> {trigger}")

# --- DEPENDENCY BOOTSTRAP ---
def bootstrap(install_reqs=True):
    """Ensures we are running in the correct VENV."""
    # Check if running in VENV
    is_venv = (sys.prefix != sys.base_prefix)
    
    if is_venv:
        # We are inside. Just ensure deps are there if requested.
        return

    # If not in VENV, try to find it and relaunch
    if sys.platform == "win32":
        venv_python = VENV_PATH / "Scripts" / "python.exe"
    else:
        venv_python = VENV_PATH / "bin" / "python3"

    if not venv_python.exists():
        print(f"❌ VENV missing at {VENV_PATH}")
        print("   Creating VENV...")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV_PATH)])
        # Re-verify
        if not venv_python.exists():
            print("❌ VENV creation failed. Please install python3-venv.")
            sys.exit(1)

    # Relaunch script with the venv python
    print(f"--> Relaunching inside VENV: {venv_python}")
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

def get_project_path(project_slug):
    return LINUX_PROJECTS_ROOT / project_slug

def save_config(project_slug, data):
    path = get_project_path(project_slug) / "project_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f: json.dump(data, f, indent=4)

def load_config(project_slug):
    path = get_project_path(project_slug) / "project_config.json"
    if not path.exists(): return None
    with open(path, 'r') as f: return json.load(f)

def slugify(text):
    return re.sub(r'[\W_]+', '_', text.lower()).strip('_')