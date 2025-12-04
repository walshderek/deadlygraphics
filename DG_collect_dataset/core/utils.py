# Script Name: core/utils.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
import sys, os, re, json, csv, subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent 
VENV_PATH = ROOT_DIR / ".venv"
REQUIREMENTS_PATH = ROOT_DIR / "core" / "requirements.txt"
LINUX_PROJECTS_ROOT = ROOT_DIR / "outputs" 
LINUX_DATASETS_ROOT = ROOT_DIR / "datasets" 
DB_PATH = ROOT_DIR / "Database" / "trigger_words.csv"
DIRS = {"scrape": "00_scraped", "crop": "01_cropped", "caption": "02_captions", "master": "03_master_1024", "downsample": "04_downsampled", "publish": "05_publish"}

def bootstrap(install_reqs=False):
    is_venv = (sys.prefix != sys.base_prefix)
    if is_venv: return
    venv_python = VENV_PATH / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python3")
    if not venv_python.exists():
        print(f"❌ VENV missing. Run: python3 -m venv .venv"); sys.exit(1)
    try: subprocess.check_call([str(venv_python)] + sys.argv); sys.exit(0)
    except: sys.exit(1)

def get_project_path(slug): return LINUX_PROJECTS_ROOT / slug
def save_config(slug, data):
    p = get_project_path(slug) / "project_config.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w') as f: json.dump(data, f, indent=4)
def load_config(slug):
    p = get_project_path(slug) / "project_config.json"
    return json.load(open(p)) if p.exists() else None
def slugify(text): return re.sub(r'[\W_]+', '_', text.lower()).strip('_')