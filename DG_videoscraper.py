# Script Name: DG_videoscraper.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Smart video downloader. Handles Opera (VPN) installation and VDH-style sniffing.

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
    # Dependencies required for Opera & Sniffing
    required = [
        'setuptools', 
        'blinker<1.8.0', # Fixes selenium-wire crash
        'webdriver-manager', 
        'yt-dlp', 
        'tqdm', 
        'requests', 
        'beautifulsoup4', 
        'selenium', 
        'selenium-wire'
    ]
    
    missing = []
    for pkg in required:
        pkg_name = pkg.split('<')[0].split('>')[0].split('=')[0]
        try:
            import_name = pkg_name.replace('-', '_')
            if pkg_name == 'beautifulsoup4': import_name = 'bs4'
            if pkg_name == 'selenium-wire': import_name = 'seleniumwire'
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        log(f"Missing/Updating dependencies: {', '.join(missing)}")
        log("Attempting auto-install...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
            log("Dependencies installed.")
        except subprocess.CalledProcessError:
            print("\n❌ AUTOMATIC INSTALL FAILED.")
            print(f"Run this manually:\n{sys.executable} -m pip install {' '.join(missing)}")
            sys.exit(1)

def check_and_install_opera():
    """Checks for Opera. If missing, prints command to install."""
    if shutil.which('opera'): return shutil.which('opera')
    if os.path.exists("/usr/bin/opera"): return "/usr/bin/opera"
    
    # Check for Opera Stable specifically
    if shutil.which('opera-stable'): return shutil.which('opera-stable')

    log("Opera Browser not found. Installing...")
    
    # Since this runs interactively in user terminal, sudo checks are safe here
    if get_os_type() in ["WSL", "LINUX"]:
        try:
            print("\n[INFO] Installing Opera. You may be asked for your sudo password.")
            subprocess.run("wget -q -O - https://deb.opera.com/archive.key | sudo apt-key add -", shell=True, check=True)
            subprocess.run("sudo sh -c 'echo \"deb https://deb.opera.com/opera-stable/ stable non-free\" > /etc/apt/sources.list.d/opera-stable.list'", shell=True, check=True)
            subprocess.run("sudo apt-get update", shell=True, check=True)
            subprocess.run("sudo apt-get install -y opera-stable", shell=True, check=True)
            log("Opera installed successfully.")
            return "/usr/bin/opera"
        except Exception as e:
            print(f"❌ Install failed: {e}")
            print("Run manually: sudo apt-get install opera-stable")
            sys.exit(1)
    else:
        print("Please install Opera manually on Windows.")
        sys.exit(1)

# --- Mode 1: Smart Direct Downloader ---
def download_with_requests(url, output_path, force_fresh=False):
    import requests
    from tqdm import tqdm
    
    filename = os.path.basename(urlparse(url).path)
    if not filename or len(filename) < 3: filename = "video_direct.mp4"
    if not os.path.splitext(filename)[1]: filename += ".mp4"
             
    output_file = os.path.join(output_path, filename)
    
    if os.path.exists(output_file) and not force_fresh:
        log(f"File exists: {filename}. Skipping.")
        return True

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
        "Referer": "https://noodlemagazine.com/", 
        "Accept": "*/*"
    }
    
    log(f"Downloading direct link: {filename}")
    try:
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            with open(output_file, 'wb') as f, tqdm(desc=filename[:20], total=total_size, unit='B', unit_scale=True, unit_divisor=1024) as bar:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bar.update(len(chunk))
        return True
    except Exception as e:
        log(f"Direct download failed: {e}")
        return False

# --- Mode 2: VDH Browser Sniffer (Opera) ---
def recursive_click_play(driver, depth=0, max_depth=4):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    if depth > max_depth: return False
    try:
        btn = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[class*='play'], div[class*='play'], video, [aria-label*='Play']")))
        driver.execute_script("arguments[0].click();", btn)
        log(f"Clicked play button at depth {depth}")
        return True
    except: pass
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for frame in iframes:
            try:
                driver.switch_to.frame(frame)
                if recursive_click_play(driver, depth + 1, max_depth):
                    driver.switch_to.default_content()
                    return True
                driver.switch_to.parent_frame()
            except: driver.switch_to.parent_frame()
    except: pass
    return False

def scrape_stream_url(url, debug=False):
    from seleniumwire import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.opera import OperaDriverManager
    from selenium.webdriver.chrome.options import Options
    
    log(f"Sniffing with Opera: {url}")
    driver = None
    try:
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Use existing profile to keep VPN
        user_data = os.path.expanduser("~/.config/opera")
        if os.path.exists(user_data):
            options.add_argument(f"user-data-dir={user_data}")
            
        if not debug: options.add_argument('--headless=new')
        
        # Point to Opera Binary
        opera_bin = check_and_install_opera()
        options.binary_location = opera_bin

        # Driver Manager
        driver_path = OperaDriverManager().install()
        service = Service(driver_path)
        
        driver = webdriver.Chrome(service=service, options=options)
        driver.scopes = [r'.*\.m3u8.*', r'.*\.mp4.*', r'.*\.webm.*']
        
        driver.get(url)
        time.sleep(5)
        
        if not recursive_click_play(driver):
            log("No play button found")
            
        log("Waiting 10s for network traffic...")
        time.sleep(10)
        
        for req in reversed(driver.requests):
            if any(ext in req.url for ext in ['.m3u8', '.mp4', '.webm']):
                log(f"✅ FOUND STREAM: {req.url[:60]}...")
                tf = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
                tf.write("# Netscape HTTP Cookie File\n")
                for c in driver.get_cookies():
                    tf.write(f"{c.get('domain')}\tTRUE\t{c.get('path')}\t{str(c.get('secure')).upper()}\t{c.get('expiry', 0)}\t{c.get('name')}\t{c.get('value')}\n")
                tf.close()
                return req.url, tf.name
        log("No stream found")
        return None, None
    except Exception as e:
        log(f"Browser failed: {e}")
        return None, None
    finally:
        if driver: driver.quit()

def download_file(url, output_dir, cookie_file=None, referer=None, force_fresh=False):
    import yt_dlp
    opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'no_overwrites': not force_fresh,
    }
    if cookie_file: opts['cookiefile'] = cookie_file
    if referer: opts['http_headers'] = {'Referer': referer}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([url])
        return True
    except Exception as e:
        log(f"yt-dlp download failed: {e}")
        return False

def main():
    check_and_install_dependencies()
    
    if not os.path.exists(DEFAULT_CHECKLIST):
        log(f"Creating empty checklist: {DEFAULT_CHECKLIST}")
        with open(DEFAULT_CHECKLIST, "w") as f:
            f.write("# Paste URLs here (one per line)\n")
    
    with open(DEFAULT_CHECKLIST, "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
    if not urls:
        log(f"No URLs in {DEFAULT_CHECKLIST}.")
        sys.exit(0)

    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)
    
    # Ensure Opera is present if needed
    if any(not re.search(r'\.(mp4|m3u8|webm)', u) for u in urls):
        check_and_install_opera()

    print(f"🚀 Processing {len(urls)} URLs...")
    for url in urls:
        if re.search(r'\.(mp4|m3u8|webm)', url):
            log(f"--> Direct link: {url[:30]}...")
            if "noodlemagazine" in url or "pvvstream" in url:
                 download_with_requests(url, output_dir)
            else:
                 download_file(url, output_dir, referer=url)
            continue
            
        stream_url, cookies = scrape_stream_url(url, debug=False)
        if stream_url:
            download_file(stream_url, output_dir, cookies, referer=url)
            if cookies and os.path.exists(cookies): os.remove(cookies)
        else:
            log(f"❌ Failed: {url}")

if __name__ == "__main__":
    main()