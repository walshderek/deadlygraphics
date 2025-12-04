# Script Name: DG_videoscraper.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Smart video downloader with VDH-style sniffing and direct link bypass.

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

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)

def log(msg):
    print(f"--> {msg}")

# --- OS & Path Handling ---
def get_os_type():
    if platform.system() == "Windows": return "WIN"
    if "microsoft" in platform.uname().release.lower(): return "WSL"
    return "LINUX"

# --- Dependency Management ---
def check_and_install_dependencies():
    """Checks for required pip packages and installs them."""
    required = ['yt-dlp', 'tqdm', 'requests', 'beautifulsoup4', 'selenium', 'undetected-chromedriver', 'selenium-wire']
    
    missing = []
    for pkg in required:
        try:
            import_name = pkg.replace('-', '_')
            if pkg == 'beautifulsoup4': import_name = 'bs4'
            if pkg == 'undetected-chromedriver': import_name = 'undetected_chromedriver'
            if pkg == 'selenium-wire': import_name = 'seleniumwire'
            
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        log(f"Missing dependencies: {', '.join(missing)}")
        log("Attempting auto-install...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
            log("Dependencies installed.")
        except subprocess.CalledProcessError:
            print("\n❌ AUTOMATIC INSTALL FAILED.")
            print(f"Please run this command manually:\n{sys.executable} -m pip install {' '.join(missing)}")
            sys.exit(1)

def check_and_install_chromium():
    """Locates or installs Chrome."""
    if os.path.exists("/usr/bin/google-chrome"):
        return "/usr/bin/google-chrome"

    path = shutil.which('google-chrome') or shutil.which('chromium-browser') or shutil.which('chrome')
    if path:
        return path
    
    print("\n❌ Chrome Browser not found.")
    if get_os_type() in ["WSL", "LINUX"]:
        print("Please run this command manually to install it:")
        print("wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -")
        print("sudo sh -c 'echo \"deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main\" > /etc/apt/sources.list.d/google-chrome.list'")
        print("sudo apt-get update && sudo apt-get install -y google-chrome-stable")
    else:
        print("Please install Google Chrome manually on Windows.")
    sys.exit(1)

# --- Mode 1: Smart Direct Downloader ---
def download_with_requests(url, output_path, force_fresh=False):
    """
    Downloads a direct video URL using 'requests' with specific headers.
    This bypasses yt-dlp/selenium for direct links that need a Referer.
    """
    import requests
    from tqdm import tqdm
    
    # Extract filename
    filename = os.path.basename(urlparse(url).path)
    if not filename or len(filename) < 3: filename = "video_direct.mp4"
    if not os.path.splitext(filename)[1]: filename += ".mp4"
             
    output_file = os.path.join(output_path, filename)
    
    if os.path.exists(output_file) and not force_fresh:
        log(f"File exists: {filename}. Skipping.")
        return True

    # Headers (Mimicking Browser/Curl)
    # NOTE: Referer is critical for some sites (e.g. NoodleMagazine)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://noodlemagazine.com/", 
        "Accept": "*/*"
    }
    
    log(f"Downloading direct link: {filename}")
    
    try:
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            
            with open(output_file, 'wb') as f, tqdm(
                desc=filename[:20],
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bar.update(len(chunk))
        return True
    except Exception as e:
        log(f"Direct download failed: {e}")
        return False

# --- Mode 2: VDH Browser Sniffer ---
def recursive_click_play(driver, depth=0, max_depth=4):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    if depth > max_depth: return False

    try:
        # Broad selector for any play button
        btn = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[class*='play'], div[class*='play'], video, [aria-label*='Play']")))
        driver.execute_script("arguments[0].click();", btn)
        log(f"Clicked play button at depth {depth}")
        return True
    except:
        pass

    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for frame in iframes:
            try:
                driver.switch_to.frame(frame)
                if recursive_click_play(driver, depth + 1, max_depth):
                    driver.switch_to.default_content()
                    return True
                driver.switch_to.parent_frame()
            except:
                driver.switch_to.parent_frame()
    except:
        pass
    return False

def scrape_stream_url(url, browser_path, debug=False):
    from seleniumwire import undetected_chromedriver as uc
    
    log(f"Sniffing: {url}")
    driver = None
    
    try:
        opts = uc.ChromeOptions()
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--mute-audio')
        opts.add_argument('--window-size=1920,1080')
        if not debug: opts.add_argument('--headless=new')
        
        driver = uc.Chrome(options=opts, browser_executable_path=browser_path)
        driver.scopes = [r'.*\.m3u8.*', r'.*\.mp4.*', r'.*\.webm.*']
        
        driver.get(url)
        time.sleep(5)
        
        if not recursive_click_play(driver):
            log("No play button found (might be autoplay or hidden)")
            
        log("Waiting 10s for network traffic...")
        time.sleep(10)
        
        for req in reversed(driver.requests):
            if any(ext in req.url for ext in ['.m3u8', '.mp4', '.webm']):
                log(f"✅ FOUND STREAM: {req.url[:60]}...")
                
                # Save Cookies
                tf = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
                tf.write("# Netscape HTTP Cookie File\n")
                for c in driver.get_cookies():
                    tf.write(f"{c.get('domain')}\tTRUE\t{c.get('path')}\t{str(c.get('secure')).upper()}\t{c.get('expiry', 0)}\t{c.get('name')}\t{c.get('value')}\n")
                tf.close()
                
                return req.url, tf.name
                
        log("No stream found in network history")
        return None, None

    except Exception as e:
        log(f"Browser crashed or failed: {e}")
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
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        log(f"yt-dlp download failed: {e}")
        return False

# --- Main Logic ---
def main():
    check_and_install_dependencies()
    
    # 1. Setup Checklist File
    if not os.path.exists(DEFAULT_CHECKLIST):
        log(f"Creating empty checklist: {DEFAULT_CHECKLIST}")
        with open(DEFAULT_CHECKLIST, "w") as f:
            f.write("# Paste URLs here (one per line)\n")
            f.write("# https://example.com/video\n")
    
    with open(DEFAULT_CHECKLIST, "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
    if not urls:
        log(f"No URLs found in {DEFAULT_CHECKLIST}. Add some and run again!")
        sys.exit(0)

    # 2. Setup Output Dir
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)
    
    # 3. Setup Browser (Only needed if we have web links)
    browser_path = None
    if any(not re.search(r'\.(mp4|m3u8|webm)', u) for u in urls):
        browser_path = check_and_install_chromium()

    print(f"🚀 Processing {len(urls)} URLs...")
    
    for url in urls:
        # MODE 1: Direct Link (Smart Bypass)
        if re.search(r'\.(mp4|m3u8|webm)', url):
            log(f"--> Direct link detected: {url[:30]}...")
            if "noodlemagazine" in url or "pvvstream" in url:
                 download_with_requests(url, output_dir)
            else:
                 # Assume generic direct link, try basic download
                 download_file(url, output_dir, referer=url)
            continue
            
        # MODE 2: Webpage (VDH Sniffer)
        stream_url, cookies = scrape_stream_url(url, browser_path, debug=False)
        
        if stream_url:
            download_file(stream_url, output_dir, cookies, referer=url)
            if cookies and os.path.exists(cookies): os.remove(cookies)
        else:
            log(f"❌ Failed: {url}")

if __name__ == "__main__":
    main()