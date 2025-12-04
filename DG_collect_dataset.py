# Script Name: DG_collect_dataset.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Bulk media downloader for building AI datasets. Supports Images, Videos, and Archives.

import sys
import os
import subprocess
import time
import shutil
import logging
import argparse
import concurrent.futures
from urllib.parse import urlparse, unquote
import re
import platform
import mimetypes

# --- Configuration ---
DEFAULT_CHECKLIST = "dataset_checklist.txt"
MAX_WORKERS = 5  # How many concurrent downloads

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def log(msg):
    print(f"--> {msg}")

def get_os_type():
    if platform.system() == "Windows": return "WIN"
    if "microsoft" in platform.uname().release.lower(): return "WSL"
    return "LINUX"

# --- Dependency Management ---
def check_and_install_dependencies():
    required = ['requests', 'tqdm', 'yt-dlp', 'beautifulsoup4']
    
    missing = []
    for pkg in required:
        try:
            import_name = pkg.replace('-', '_')
            if pkg == 'beautifulsoup4': import_name = 'bs4'
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        log(f"Installing dependencies: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
        except:
            print("\n❌ Auto-install failed. Run manually:")
            print(f"{sys.executable} -m pip install {' '.join(missing)}")
            sys.exit(1)

# --- Path Logic ---
def determine_output_dir():
    # Priority: H: Drive -> Local 'datasets' folder
    windows_drive = "/mnt/h/My Drive/AI/Datasets"
    
    if os.path.exists("/mnt/h"):
        if not os.path.exists(windows_drive):
            try:
                os.makedirs(windows_drive)
                return windows_drive
            except:
                pass # Fallback if H is read-only for some reason
        else:
            return windows_drive
            
    local_dir = "datasets"
    os.makedirs(local_dir, exist_ok=True)
    return local_dir

# --- Download Logic ---
def get_filename_from_url(url, content_type=None):
    # 1. Try from URL path
    path = urlparse(url).path
    name = os.path.basename(unquote(path))
    
    # 2. Clean name
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    
    # 3. Ensure extension
    if not os.path.splitext(name)[1]:
        if content_type:
            ext = mimetypes.guess_extension(content_type)
            if ext: name += ext
        else:
            name += ".unknown"
            
    if len(name) > 100: name = name[:100] # Truncate if insane
    if not name: name = f"file_{int(time.time())}"
    
    return name

def download_direct(url, output_dir):
    import requests
    from tqdm import tqdm
    
    try:
        # Stream request to get headers first
        with requests.get(url, stream=True, timeout=15) as r:
            r.raise_for_status()
            
            filename = get_filename_from_url(url, r.headers.get('content-type'))
            output_path = os.path.join(output_dir, filename)
            
            if os.path.exists(output_path):
                log(f"Skipping (Exists): {filename}")
                return True
            
            total_size = int(r.headers.get('content-length', 0))
            
            log(f"Downloading: {filename}")
            with open(output_path, 'wb') as f, tqdm(
                total=total_size, 
                unit='B', 
                unit_scale=True, 
                desc=filename[:15]
            ) as bar:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bar.update(len(chunk))
        return True
    except Exception as e:
        log(f"Direct Download Failed {url}: {e}")
        return False

def download_ytdlp(url, output_dir):
    import yt_dlp
    
    opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info: return False
            
            title = info.get('title', 'video')
            log(f"Processing Video: {title}")
            ydl.download([url])
        return True
    except:
        return False

def process_url(url, output_dir):
    if not url: return
    
    # 1. Try as direct file first (fastest)
    if re.search(r'\.(jpg|jpeg|png|webp|gif|zip|tar|gz|mp4|mkv)$', url, re.IGNORECASE):
        if download_direct(url, output_dir): return

    # 2. Try yt-dlp (handles YouTube, Twitter, Reddit, etc.)
    if download_ytdlp(url, output_dir): return

    # 3. Fallback to direct (if extension was hidden)
    if download_direct(url, output_dir): return
    
    log(f"❌ Could not download: {url}")

def main():
    check_and_install_dependencies()
    
    # Setup Checklist
    if not os.path.exists(DEFAULT_CHECKLIST):
        with open(DEFAULT_CHECKLIST, "w") as f:
            f.write("# Add image/video URLs here\n")
            f.write("# https://example.com/image.jpg\n")
        log(f"Created empty checklist: {DEFAULT_CHECKLIST}")
    
    with open(DEFAULT_CHECKLIST, "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not urls:
        log("Checklist is empty. Add URLs and run again.")
        sys.exit(0)

    output_dir = determine_output_dir()
    log(f"Saving Dataset to: {output_dir}")

    # Parallel Execution
    log(f"Starting {MAX_WORKERS} threads for {len(urls)} items...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_url, url, output_dir) for url in urls]
        for _ in concurrent.futures.as_completed(futures):
            pass # Just wait for completion

    log("✅ Dataset Collection Complete.")

if __name__ == "__main__":
    main()