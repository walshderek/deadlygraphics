# Script Name: DG_videoscraper.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: 3-Tier Video Scraper: API/Direct -> Chrome -> Opera (VPN).

import sys
import os
import subprocess
import time
import shutil
import logging
import argparse
from urllib.parse import urlparse
import re
import tempfile
import platform
import json

# --- Configuration ---
DEFAULT_CHECKLIST = "scrapervideo_checklist.txt"

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def log(msg):
    print(f"--> {msg}")

def get_os_type():
    if platform.system() == "Windows": return "WIN"
    if "microsoft" in platform.uname().release.lower(): return "WSL"
    return "LINUX"

# --- Dependency Management ---
def check_and_install_dependencies():
    # Deps for BOTH Chrome and Opera logic
    required = [
        'setuptools', 'blinker<1.8.0', 'webdriver-manager', 
        'yt-dlp', 'tqdm', 'requests', 'beautifulsoup4', 
        'selenium', 'selenium-wire', 'undetected-chromedriver'
    ]
    
    missing = []
    for pkg in required:
        pkg_name = pkg.split('<')[0].split('>')[0].split('=')[0]
        try:
            import_name = pkg_name.replace('-', '_')
            if pkg_name == 'beautifulsoup4': import_name = 'bs4'
            if pkg_name == 'selenium-wire': import_name = 'seleniumwire'
            if pkg_name == 'undetected-chromedriver': import_name = 'undetected_chromedriver'
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        log(f"Missing/Updating dependencies: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
            log("Dependencies installed.")
        except subprocess.CalledProcessError:
            print("\n❌ AUTOMATIC INSTALL FAILED. Run manually:")
            print(f"{sys.executable} -m pip install {' '.join(missing)}")
            sys.exit(1)

def check_browser_installed(browser_name):
    """Checks if a specific browser binary exists."""
    if browser_name == "chrome":
        return shutil.which('google-chrome') or shutil.which('google-chrome-stable')
    elif browser_name == "opera":
        return shutil.which('opera') or shutil.which('opera-stable')
    return None

# ==========================================
# TIER 1: API / DIRECT DOWNLOAD
# ==========================================
def attempt_api_direct(url, output_dir):
    import requests
    from tqdm import tqdm
    
    # 1. Direct Link Check
    if re.search(r'\.(mp4|m3u8|webm)(\?.*)?$', url):
        log(f"[Tier 1] Direct media link detected.")
        return download_file(url, output_dir, referer=url)

    # 2. Simple Pornhub API Check (Example of expanding API logic)
    if "pornhub.com/view_video.php" in url:
        viewkey = re.search(r'viewkey=([^&]+)', url)
        if viewkey:
            log(f"[Tier 1] Attempting Pornhub API fetch...")
            # Ideally we'd implement full API logic here. 
            # For now, we return False to let Chrome handle it reliably.
            # Only implementing if we have a known working API key/method.
            return False 

    return False

# ==========================================
# TIER 2: CHROME SNIFFER (Undetected)
# ==========================================
def attempt_chrome_sniff(url):
    from seleniumwire import undetected_chromedriver as uc
    
    if not check_browser_installed("chrome"):
        log("[Tier 2] Chrome not found. Skipping