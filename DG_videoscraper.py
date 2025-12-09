# Script Name: DG_videoscraper.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Smart video downloader. 3-Tier fallback. Interactive Sudo.

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

DEFAULT_CHECKLIST = "scrapervideo_checklist.txt"
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def log(msg):
    print(f"--> {msg}")

def get_os_type():
    if platform.system() == "Windows": return "WIN"
    if "microsoft" in platform.uname().release.lower(): return "WSL"
    return "LINUX"

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
        log(f"Installing dependencies: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
        except:
            print("\n❌ AUTO-INSTALL FAILED. Run manually:"); 
            print(f"{sys.executable} -m pip install {' '.join(missing)}"); sys.exit(1)
    
    if not shutil.which("ffmpeg"):
        print("\n❌ FFMPEG missing. Please run: sudo apt-get install -y ffmpeg")
        sys.exit(1)

def check_and_install_opera():
    if shutil.which('opera') or shutil.which('opera-stable') or os.path.exists("/usr/bin/opera"):
        return shutil.which('opera') or shutil.which('opera-stable') or "/usr/bin/opera"

    log("Opera not found. Installing...")
    if get_os_type() in ["WSL", "LINUX"]:
        try:
            print("\n[INFO] Installing Opera. Enter Sudo Password if asked:")
            subprocess.run("wget -q -O - https://deb.opera.com/archive.key | sudo apt-key add -", shell=True, check=True)
            subprocess.run("sudo sh -c 'echo \"deb https://deb.opera.com/opera-stable/ stable non-free\" > /etc/apt/sources.list.d/opera-stable.list'", shell=True, check=True)
            subprocess.run("sudo apt-get update", shell=True, check=True)
            subprocess.run("sudo apt-get install -y opera-stable", shell=True, check=True)
            return "/usr/bin/opera"
        except:
            print("Install failed. Run manually: sudo apt-get install opera-stable"); sys.exit(1)
    else:
        print("Install Opera manually on Windows."); sys.exit(1)

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
            name = c.get('name', ''); value = c.get('value', '')
            if name and value:
                tf.write(f"{domain}\tTRUE\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
        tf.close(); return tf.name
    except: return None

def download_file(url, output_dir, cookie_file=None, referer=None, title=None):
    import yt_dlp
    name = f"{title}.%(ext)s" if title else "%(title)s.%(ext)s"
    opts = {
        'outtmpl': os.path.join(output_dir, name),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'noplaylist': True, 'quiet': False, 'no_warnings': False,
        'http_headers': {'Referer': referer} if referer else {},
    }
    if cookie_file: opts['cookiefile'] = cookie_file
    try:
        with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([url])
        return True
    except Exception as e: log(f"DL failed: {e}"); return False

# ... [Mode 1 (Requests) and Mode 2 (Sniffers) same as previous correct logic] ...
# I am re-pasting the critical sniffer functions below to ensure they are in the file

def download_with_requests(url, output_path, force_fresh=False):
    import requests
    from tqdm import tqdm
    filename = os.path.basename(urlparse(url).path)
    if len(filename) < 3: filename = "video_direct.mp4"
    if not os.path.splitext(filename)[1]: filename += ".mp4"
    output_file = os.path.join(output_path, filename)
    if os.path.exists(output_file) and not force_fresh: log(f"Exists: {filename}"); return True
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://noodlemagazine.com/", "Accept": "*/*"}
    try:
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            total = int(r.headers.get('content-length', 0))
            with open(output_file, 'wb') as f, tqdm(total=total, unit='B', unit_scale=True) as bar:
                for chunk in r.iter_content(8192): f.write(chunk); bar.update(len(chunk))
        return True
    except Exception as e: log(f"Direct fail: {e}"); return False

def attempt_api_direct(url, output_dir):
    if re.search(r'\.(mp4|m3u8|webm)(\?.*)?$', url):
        log("Direct link detected."); return download_with_requests(url, output_dir)
    return False

def recursive_click_play(driver, depth=0):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    if depth > 4: return False
    try:
        btn = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[class*='play'], div[class*='play'], video, [aria-label*='Play']")))
        driver.execute_script("arguments[0].click();", btn)
        return True
    except: pass
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for frame in iframes:
            try:
                driver.switch_to.frame(frame)
                if recursive_click_play(driver, depth+1): driver.switch_to.default_content(); return True
                driver.switch_to.parent_frame()
            except: driver.switch_to.parent_frame()
    except: pass
    return False

def attempt_sniff(url, browser, debug=False):
    from seleniumwire import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.opera import OperaDriverManager
    from seleniumwire import undetected_chromedriver as uc

    driver = None
    try:
        if browser == 'chrome':
            opts = uc.ChromeOptions()
            opts.add_argument('--no-sandbox'); opts.add_argument('--disable-dev-shm-usage'); opts.add_argument('--mute-audio')
            if not debug: opts.add_argument('--headless=new')
            driver = uc.Chrome(options=opts)
        else: # Opera
            opts = Options()
            opts.add_experimental_option('w3c', True)
            opts.add_argument('--no-sandbox'); opts.add_argument('--disable-dev-shm-usage')
            if not debug: opts.add_argument('--headless=new')
            opts.binary_location = check_and_install_opera()
            driver_path = OperaDriverManager().install()
            driver = webdriver.Chrome(service=Service(driver_path), options=opts)

        driver.scopes = [r'.*\.m3u8.*', r'.*\.mp4.*', r'.*\.webm.*']
        driver.get(url); time.sleep(5)
        
        clean_title = re.sub(r'[\\/*?:"<>|]', "", driver.title).strip() or "video"
        recursive_click_play(driver); time.sleep(15)

        best_stream = None; max_size = 0
        for req in reversed(driver.requests):
            if req.response and any(ext in req.url for ext in ['.m3u8', '.mp4', '.webm']):
                clen = int(req.response.headers.get('Content-Length', 0))
                if '.m3u8' in req.url: return req.url, save_cookies_safe(driver), clean_title
                size_mb = clen / (1024*1024)
                if size_mb > max_size: max_size = size_mb; best_stream = req.url
        
        if best_stream and max_size > 5:
            log(f"Found Stream ({max_size:.2f} MB)"); return best_stream, save_cookies_safe(driver), clean_title
        return None, None, None
    except Exception as e: log(f"{browser} failed: {e}"); return None, None, None
    finally:
        if driver: driver.quit()

def load_github_token():
    if os.name == 'nt': cred_file = r"C:\credentials\credentials.json"
    else: cred_file = "/mnt/c/credentials/credentials.json"
    if not os.path.exists(cred_file): return None
    try:
        with open(cred_file, 'r') as f: return json.load(f).get("github", {}).get("token", "")
    except: return None

def main():
    check_and_install_dependencies()
    if not os.path.exists(DEFAULT_CHECKLIST):
        with open(DEFAULT_CHECKLIST, "w") as f: f.write("# URLs here\n")
    
    with open(DEFAULT_CHECKLIST, "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    if not urls: log(f"No URLs in {DEFAULT_CHECKLIST}."); sys.exit(0)

    out_dir = "/mnt/h/My Drive/AI/Downloads" if os.path.exists("/mnt/h") else "downloads"
    os.makedirs(out_dir, exist_ok=True)
    log(f"Saving to: {out_dir}")

    # Inject Auth for Opera
    token = load_github_token()
    if token: os.environ['GH_TOKEN'] = token

    print(f"🚀 Processing {len(urls)} URLs...")
    for url in urls:
        print(f"\n--- Processing: {url[:40]}... ---")
        if attempt_api_direct(url, out_dir): continue
        
        s_url, cookie, title = attempt_sniff(url, 'chrome')
        if s_url: 
            download_file(s_url, out_dir, cookie, url, title)
            if cookie: os.remove(cookie)
            continue
            
        s_url, cookie, title = attempt_sniff(url, 'opera')
        if s_url:
            download_file(s_url, out_dir, cookie, url, title)
            if cookie: os.remove(cookie)
            continue
        log("❌ All methods failed.")

if __name__ == "__main__":
    main()