# Script Name: DG_videoscraper.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Smart video downloader. Uses GH Token to prevent rate limits.

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

# Path Logic
if os.name == 'nt':
    CREDENTIALS_FILE = r"C:\credentials\credentials.json"
else:
    CREDENTIALS_FILE = "/mnt/c/credentials/credentials.json"

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def log(msg):
    print(f"--> {msg}")

def get_os_type():
    if platform.system() == "Windows": return "WIN"
    if "microsoft" in platform.uname().release.lower(): return "WSL"
    return "LINUX"

# --- Credentials ---
def load_github_token():
    """Loads GH Token to unblock WebDriver Manager rate limits."""
    if not os.path.exists(CREDENTIALS_FILE):
        return None
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            data = json.load(f)
            return data.get("github", {}).get("token", "")
    except:
        return None

# --- Dependency Management ---
def check_and_install_dependencies():
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
    return False

# ==========================================
# TIER 2: CHROME SNIFFER (Undetected)
# ==========================================
def attempt_chrome_sniff(url):
    from seleniumwire import undetected_chromedriver as uc
    
    if not check_browser_installed("chrome"):
        log("[Tier 2] Chrome not found. Skipping.")
        return None, None

    log(f"[Tier 2] Sniffing with Chrome: {url}")
    driver = None
    try:
        opts = uc.ChromeOptions()
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--mute-audio')
        opts.add_argument('--headless=new')
        
        driver = uc.Chrome(options=opts)
        return run_vdh_logic(driver, url)
    except Exception as e:
        log(f"[Tier 2] Chrome Failed: {e}")
        return None, None
    finally:
        if driver: driver.quit()

# ==========================================
# TIER 3: OPERA SNIFFER (VPN Capable)
# ==========================================
def attempt_opera_sniff(url):
    from seleniumwire import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.opera import OperaDriverManager
    from selenium.webdriver.chrome.options import Options
    
    if not check_browser_installed("opera"):
        log("[Tier 3] Opera not found. Skipping.")
        return None, None

    log(f"[Tier 3] Sniffing with Opera: {url}")
    
    # AUTH INJECTION: Fixes the API Rate Limit Error
    token = load_github_token()
    if token:
        os.environ['GH_TOKEN'] = token

    driver = None
    try:
        options = Options()
        options.add_experimental_option('w3c', True)
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        user_data = os.path.expanduser("~/.config/opera")
        if os.path.exists(user_data):
            options.add_argument(f"user-data-dir={user_data}")
        
        options.binary_location = check_browser_installed("opera")
        options.add_argument('--headless=new')

        driver_path = OperaDriverManager().install()
        service = Service(driver_path)
        
        driver = webdriver.Chrome(service=service, options=options)
        return run_vdh_logic(driver, url)
    except Exception as e:
        log(f"[Tier 3] Opera Failed: {e}")
        return None, None
    finally:
        if driver: driver.quit()

# ==========================================
# SHARED LOGIC
# ==========================================
def run_vdh_logic(driver, url):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    driver.scopes = [r'.*\.m3u8.*', r'.*\.mp4.*', r'.*\.webm.*']
    driver.get(url)
    time.sleep(5)
    
    def click_play(d, depth=0):
        if depth > 4: return False
        try:
            btn = WebDriverWait(d, 1).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[class*='play'], div[class*='play'], video, [aria-label*='Play']")))
            d.execute_script("arguments[0].click();", btn)
            return True
        except: pass
        try:
            iframes = d.find_elements(By.TAG_NAME, "iframe")
            for frame in iframes:
                try:
                    d.switch_to.frame(frame)
                    if click_play(d, depth + 1):
                        d.switch_to.default_content()
                        return True
                    d.switch_to.parent_frame()
                except: d.switch_to.parent_frame()
        except: pass
        return False

    if not click_play(driver):
        log("No play button found (autoplay?)")
        
    log("Waiting 15s for streams...")
    time.sleep(15)
    
    best_stream = None
    max_size = 0
    
    # Filter for LARGEST stream (ignore ads)
    for req in reversed(driver.requests):
        if req.response and any(ext in req.url for ext in ['.m3u8', '.mp4', '.webm']):
            content_len = int(req.response.headers.get('Content-Length', 0))
            
            if '.m3u8' in req.url:
                log(f"✅ Found HLS Stream: {req.url[:60]}...")
                return req.url, save_cookies_safe(driver)
            
            file_size_mb = content_len / (1024 * 1024)
            if file_size_mb > max_size:
                max_size = file_size_mb
                best_stream = req.url
    
    # Threshold: 10MB to skip ads
    if best_stream and max_size > 10:
        log(f"✅ Found Largest Stream ({max_size:.2f} MB): {best_stream[:60]}...")
        return best_stream, save_cookies_safe(driver)
            
    return None, None

def save_cookies_safe(driver):
    try:
        tf = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        tf.write("# Netscape HTTP Cookie File\n")
        for c in driver.get_cookies():
            domain = c.get('domain', '')
            if not domain.startswith('.'): domain = '.' + domain
            path = c.get('path', '/')
            secure = str(c.get('secure', False)).upper()
            expiry = int(c.get('expiry', time.time() + 3600))
            name = c.get('name', '')
            value = c.get('value', '')
            if name and value:
                tf.write(f"{domain}\tTRUE\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
        tf.close()
        return tf.name
    except: return None

def download_file(url, output_dir, cookie_file=None, referer=None, force_fresh=False):
    import yt_dlp
    
    # Get cleaner filename if possible
    clean_name = "%(title)s.%(ext)s"
    
    # Special headers
    headers = {'Referer': referer} if referer else {}
    if "noodlemagazine" in (referer or ""):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://noodlemagazine.com/",
            "Accept": "*/*"
        }

    opts = {
        'outtmpl': os.path.join(output_dir, clean_name),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'noplaylist': True,
        'quiet': False, # Loud logs
        'no_warnings': False,
        'http_headers': headers,
        'no_overwrites': not force_fresh,
    }
    if cookie_file: opts['cookiefile'] = cookie_file
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([url])
        return True
    except Exception as e:
        log(f"Download failed: {e}")
        return False

def determine_output_dir():
    # Try Windows Drive first
    windows_drive = "/mnt/h/My Drive/AI/Downloads"
    if os.path.exists("/mnt/h"):
        if not os.path.exists(windows_drive):
            try: os.makedirs(windows_drive)
            except: return "downloads"
        return windows_drive
    return "downloads"

def main():
    check_and_install_dependencies()
    
    if not os.path.exists(DEFAULT_CHECKLIST):
        with open(DEFAULT_CHECKLIST, "w") as f: f.write("# URLs here\n")
    
    with open(DEFAULT_CHECKLIST, "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
    if not urls:
        log(f"No URLs in {DEFAULT_CHECKLIST}."); sys.exit(0)

    output_dir = determine_output_dir()
    log(f"Saving to: {output_dir}")

    print(f"🚀 Processing {len(urls)} URLs...")
    for url in urls:
        print(f"\n--- Processing: {url[:40]}... ---")
        
        if attempt_api_direct(url, output_dir): continue
        
        stream_url, cookies = attempt_chrome_sniff(url)
        if stream_url:
            download_file(stream_url, output_dir, cookies, referer=url)
            if cookies: os.remove(cookies)
            continue
            
        stream_url, cookies = attempt_opera_sniff(url)
        if stream_url:
            download_file(stream_url, output_dir, cookies, referer=url)
            if cookies: os.remove(cookies)
            continue
            
        log("❌ ALL TIERS FAILED.")

if __name__ == "__main__":
    main()