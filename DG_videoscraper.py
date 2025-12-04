import sys
import os
import subprocess
import concurrent.futures
import time
import shutil
import random
from urllib.parse import urljoin, urlparse, parse_qs
from tqdm import tqdm
import re
import json
import tempfile
import zipfile

def check_and_install_packages():
    """Ensures all required packages are installed or upgraded."""
    packages = ['yt-dlp', 'tqdm', 'requests', 'beautifulsoup4', 'selenium', 'undetected-chromedriver', 'selenium-wire']
    print("--> Checking and installing required packages...")
    for package_name in packages:
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', '--upgrade', package_name],
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError:
            print(f"--> Standard install failed for {package_name}. Retrying with --break-system-packages...")
            try:
                subprocess.check_call(
                    [sys.executable, '-m', 'pip', 'install', '--upgrade', package_name, '--break-system-packages'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
                )
            except subprocess.CalledProcessError as e:
                tqdm.write(f"❌ Critical Error: Failed to install '{package_name}'.")
                tqdm.write(f"Please install manually: '{sys.executable} -m pip install --upgrade {package_name} --break-system-packages'")
                tqdm.write(f"Error details: {e}")
                sys.exit(1)
    print("--> Package check complete.")

def check_and_install_chromium():
    """Checks if a Chrome/Chromium browser is available for selenium."""
    browser_path = "/usr/bin/google-chrome"
    if os.path.exists(browser_path):
         print(f"--> Found 'google-chrome' at {browser_path}.")
         return browser_path
    for browser in ['chromium-browser', 'google-chrome', 'chromium']:
        path = shutil.which(browser)
        if path:
            print(f"--> Found '{browser}' at {path}.")
            return path
    print("\n" + "="*60)
    print("⚠️  Chrome/Chromium browser not found, required for scraping.")
    print("--> Attempting to install 'google-chrome-stable'. You may be prompted for your password.")
    print("="*60 + "\n")
    try:
        subprocess.check_call(['wget', '-q', '-O', '-', 'https://dl.google.com/linux/linux_signing_key.pub', '|', 'sudo', 'apt-key', 'add', '-'], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, shell=True)
        subprocess.check_call(['sudo', 'sh', '-c', 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list'], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        subprocess.check_call(['sudo', 'apt-get', 'update'], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        subprocess.check_call(['sudo', 'apt-get', 'install', '-y', 'google-chrome-stable'], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        print("\n✅ Successfully installed 'google-chrome-stable'.")
        return "/usr/bin/google-chrome"
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"\n❌ Failed to install Google Chrome: {e}")
        print("Please try installing 'google-chrome-stable' or 'chromium-browser' manually.")
        sys.exit(1)

# --- NEW: The "Dumb" Downloader ---
def download_with_requests(url, output_path, pbar_instance):
    """
    Downloads a direct video URL using 'requests', mimicking the curl command.
    This bypasses yt-dlp for direct links that yt-dlp fails on.
    """
    import requests
    
    # Extract filename from URL path, ignoring query parameters
    filename = os.path.basename(urlparse(url).path)
    if not filename: # Fallback
        filename = "video.mp4"
    
    # Ensure filename has an extension
    if not os.path.splitext(filename)[1]:
        if 'm3u8' in url:
             filename += ".m3u8"
        else:
             filename += ".mp4"
             
    output_file = os.path.join(output_path, filename)
    
    # Check if file already exists
    # Note: force_fresh is accessed via global or needs passing. 
    # For simplicity here we assume overwrite unless logic added.
    if os.path.exists(output_file) and not force_fresh:
        tqdm.write(f"➡️ File already exists: {filename}. Skipping. (Use --fresh to re-download)")
        if pbar_instance.total:
             pbar_instance.n = pbar_instance.total
        else:
             pbar_instance.n = 1
        pbar_instance.refresh()
        return True

    # These headers are copied *directly* from your successful curl command
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0",
        "Accept": "video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5",
        "Accept-Language": "en-GB,en;q=0.5",
        "Connection": "keep-alive",
        # THIS IS THE MOST IMPORTANT HEADER:
        "Referer": "https://noodlemagazine.com/", 
        "Sec-Fetch-Dest": "video",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "cross-site",
    }
    
    tqdm.write(f"--> Starting 'requests' download with Referer: https://noodlemagazine.com/")
    pbar_instance.set_description_str(f"Downloading '{filename[:30]}...' (direct)")
    
    try:
        with requests.get(url, headers=headers, stream=True, timeout=20) as r:
            r.raise_for_status() # Will raise an error for 4xx/5xx
            
            total_size = int(r.headers.get('content-length', 0))
            if total_size > 0:
                pbar_instance.total = total_size
            
            with open(output_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar_instance.update(len(chunk))
        
        # Ensure progress bar completes
        if pbar_instance.total and pbar_instance.n < pbar_instance.total:
            pbar_instance.n = pbar_instance.total
        pbar_instance.set_description_str(f"✅ Download finished")
        pbar_instance.refresh()
        return True
        
    except requests.exceptions.RequestException as e:
        tqdm.write(f"❌ 'requests' download failed: {e}")
        return False
    except Exception as e:
        tqdm.write(f"❌ Error writing file: {e}")
        return False

# VDH/Selenium functions remain as a fallback for webpage URLs
def save_cookies_for_yt_dlp(driver):
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tf:
            cookies_file_path = tf.name
            tf.write("# Netscape HTTP Cookie File\n")
            for c in driver.get_cookies():
                domain = c.get('domain', '')
                path = c.get('path', '/')
                secure = str(c.get('secure', False)).upper()
                expiry = int(c.get('expiry', 0) or 0)
                name = c.get('name', '')
                value = c.get('value', '')
                if domain and name:
                    tf.write(f"{domain}\tTRUE\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
        tqdm.write(f"--> Saved session cookies to {cookies_file_path}")
        return cookies_file_path
    except Exception as cookie_err:
        tqdm.write(f"⚠️ Could not save cookies: {cookie_err}")
        return None

def find_and_click_play(driver, depth=0):
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    if depth > 4: return False
    try:
        play_btn = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.playButton, .playIcon, [data-purpose='play'], video, [class*='play-button'], [class*='player-play'], [aria-label*='Play'], [data-a-target='player-overlay-play-button']")))
        driver.execute_script("arguments[0].click();", play_btn)
        tqdm.write(f"--> Clicked play (depth {depth}).")
        return True
    except TimeoutException: pass
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes and depth < 4:
            tqdm.write(f"--> Found {len(iframes)} iframes at depth {depth}. Diving in...")
            for frame in iframes:
                try:
                    driver.switch_to.frame(frame)
                    if find_and_click_play(driver, depth + 1):
                        driver.switch_to.default_content() 
                        return True
                    driver.switch_to.parent_frame()
                except Exception as e:
                    tqdm.write(f"--> Error switching to iframe (will skip): {e}")
                    driver.switch_to.parent_frame()
    except Exception as e:
        tqdm.write(f"--> Error finding iframes: {e}")
    return False

def scrape_video_url_from_network(page_url, browser_path, use_profile=False, debug=False, proxy=None):
    from seleniumwire import undetected_chromedriver as uc
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    tqdm.write(f"--> Starting VDH network scrape for {page_url[:60]}...")
    driver = None
    cookies_file_path = None
    try:
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--mute-audio')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        if proxy:
            # (Proxy logic...)
            pass
        if use_profile:
            profile_path = check_chrome_profile()
            if profile_path:
                user_data_dir = os.path.dirname(profile_path)
                options.add_argument(f'--user-data-dir={user_data_dir}')
                options.add_argument('--profile-directory=Default')
                tqdm.write("--> Using real Chrome profile.")
            else:
                options.add_argument('--headless=new')
        else:
            options.add_argument('--headless=new')
        if debug:
            options.headless = False
            tqdm.write("--> Debug mode: Browser will be visible.")
        driver = uc.Chrome(options=options, browser_executable_path=browser_path)
        driver.scopes = [r'.*\.m3u8.*', r'.*\.mp4.*', r'.*\.webm.*', r'.*googlevideo\.com/videoplayback.*', r'.*manifest.*']
        tqdm.write("--> Loading page...")
        driver.get(page_url)
        time.sleep(5)
        cookies_file_path = save_cookies_for_yt_dlp(driver)
        try:
            consent_button = WebDriverWait(driver, 7).until(EC.element_to_be_clickable((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ok') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'enter') or contains(@class, 'accept') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree') or contains(@id, 'consent')]")))
            driver.execute_script("arguments[0].click();", consent_button)
            time.sleep(2)
            tqdm.write("--> Clicked consent/age button.")
        except TimeoutException:
            tqdm.write("--> No consent button found.")
        time.sleep(3) 
        if find_and_click_play(driver):
            tqdm.write("--> Recursive play click successful.")
        else:
            tqdm.write("--> Recursive search found no play button.")
            try:
                video_elem = driver.find_element(By.TAG_NAME, "video")
                driver.execute_script("arguments[0].click();", video_elem)
                tqdm.write("--> Clicked <video> element via JS as fallback.")
            except Exception:
                tqdm.write(f"--> No <video> tag found. Waiting for network...")
        tqdm.write("--> Waiting 10s for streams to be captured...")
        time.sleep(10)
        if debug:
            tqdm.write("\n" + "="*60)
            tqdm.write("🔍 DEBUG MODE: BROWSER IS VISIBLE")
            tqdm.write("Manually click 'Play' on the video now.")
            tqdm.write("The script will check for a video stream in 20 seconds...")
            tqdm.write("="*60 + "\n")
            time.sleep(20) 
        tqdm.write("--> Searching captured network requests...")
        video_url = None
        for req in reversed(driver.requests):
            if re.search(r'\.m3u8', req.url):
                tqdm.write(f"✅ Found HLS Stream (.m3u8): {req.url[:80]}")
                video_url = req.url
                break
        if not video_url:
            for req in reversed(driver.requests):
                if re.search(r'\.mp4', req.url):
                    tqdm.write(f"✅ Found MP4 Stream: {req.url[:80]}")
                    video_url = req.url
                    break
        if not video_url:
            for req in reversed(driver.requests):
                if re.search(r'\.webm', req.url):
                    tqdm.write(f"✅ Found WebM Stream: {req.url[:80]}")
                    video_url = req.url
                    break
        if video_url:
            return video_url, cookies_file_path
        else:
            tqdm.write("❌ No video streams found in network history.")
            return None, cookies_file_path
    except Exception as e:
        tqdm.write(f"❌ Scrape error: {e}")
        return None, cookies_file_path
    finally:
        if driver:
            del driver.requests 
            driver.quit()

def download_with_yt_dlp(url, output_path, pbar_instance, cookies_file=None, force_fresh=False, page_url=None):
    """
    Handles all downloads using yt-dlp. (Used as FALLBACK)
    """
    import yt_dlp
    h264_format = 'bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best'
    ydl_opts = {
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'retries': 5,
        'fragment_retries': 5,
        'quiet': True,
        'noprogress': True,
        'no_warnings': True,
        'format': h264_format,
        'no_overwrites': not force_fresh,
        'ignoreerrors': True,
        'cachedir': False, 
    }
    ydl_opts['http_headers'] = {'User-Agent': 'Mozilla/5.0 ...', 'Referer': page_url or url,}
    if cookies_file and os.path.exists(cookies_file):
        ydl_opts['cookiefile'] = cookies_file
        tqdm.write(f"--> Using cookies for yt-dlp: {cookies_file}")
    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total:
                pbar_instance.total = total
                pbar_instance.n = d.get('downloaded_bytes', 0)
                pbar_instance.set_postfix_str(f"{d.get('_percent_str', '')} at {d.get('_speed_str', '')}")
                pbar_instance.refresh()
        elif d['status'] == 'finished':
            if pbar_instance.total and pbar_instance.n < pbar_instance.total:
                pbar_instance.n = pbar_instance.total
            pbar_instance.set_description_str(f"✅ Download finished")
            pbar_instance.refresh()
    ydl_opts['progress_hooks'] = [progress_hook]
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'video')
            if title == 'video' and info.get('webpage_url'):
                try:
                    info_page = ydl.extract_info(page_url, download=False, force_generic_extractor=True)
                    title = info_page.get('title', 'video')
                except:
                    pass
            pbar_instance.set_description_str(f"Downloading '{title[:30]}...' (H.264)")
            ydl.download([url])
        return True
    except Exception as e:
        if isinstance(e, yt_dlp.utils.DownloadError) and 'already been downloaded' in str(e):
            tqdm.write(f"➡️ File already exists. Skipping. (Use --fresh to re-download)")
            pbar_instance.n = pbar_instance.total or 1
            pbar_instance.refresh()
            return True
        if 'HTTP Error 403' in str(e):
             tqdm.write(f"❌ yt-dlp 403 error. The cookie file may be invalid or expired for {url}")
             return False
        tqdm.write(f"❌ yt-dlp error for {url}")
        tqdm.write(f" -----------------------------------------------------")
        tqdm.write(f"   Error Type: {type(e).__name__}")
        tqdm.write(f"   Details: {str(e)}")
        tqdm.write(f" -----------------------------------------------------")
        return False

# --- MODIFIED: Checks if URL is a direct link ---
def is_direct_video_url(url):
    """Checks if a URL is a direct video link."""
    return re.search(r'\.(m3u8|mp4|webm)(\?.*)?$', url, re.IGNORECASE) is not None

def download_video_main(url, output_path, position, browser_path, force_fresh=False, debug=False):
    """
    Main download function for a single URL.
    NOW includes logic to bypass sniffing if URL is already a video.
    """
    pbar = tqdm(total=1000000, position=position, desc=f"Processing: {url[:40]}...", leave=False, 
                unit='B', unit_scale=True, bar_format='{l_bar}{bar}| {desc} {postfix}')
    cookies_file = None
    try:
        # --- THIS IS THE NEW LOGIC ---
        if is_direct_video_url(url):
            # 1. URL is ALREADY a video link (from manual step)
            tqdm.write(f"--> Direct video URL detected. Bypassing VDH sniffer.")
            
            # Use the new "dumb" downloader that mimics curl
            success = download_with_requests(url, output_path, pbar)
            
            # If 'requests' fails (e.g., it *is* an m3u8), try yt-dlp as a backup
            if not success:
                tqdm.write(f"--> 'requests' download failed. Retrying with yt-dlp...")
                success = download_with_yt_dlp(url, output_path, pbar, cookies_file=None, force_fresh=force_fresh, page_url=url)
            
            pbar.close()
            return success
        else:
            # 2. URL is a webpage. Do the full VDH scrape.
            tqdm.write(f"--> Webpage URL detected. Starting VDH network scrape...")
            pbar.set_description_str(f"Scraping {url[:40]}...")
            video_url, cookies_file = scrape_video_url_from_network(url, browser_path, use_profile=False, debug=debug)
            
            if video_url:
                success = download_with_yt_dlp(video_url, output_path, pbar, cookies_file=cookies_file, force_fresh=force_fresh, page_url=url)
                pbar.close()
                return success
            else:
                tqdm.write(f"❌ Failed to find any video stream for {url}")
                pbar.set_description_str(f"❌ Failed (no stream) {url[:30]}")
                pbar.close()
                return False
        # --- END NEW LOGIC ---

    except Exception as e:
        tqdm.write(f"❌ Critical error in download_video_main: {e}")
        pbar.set_description_str(f"❌ Failed (error) {url[:30]}")
        pbar.close()
        return False
        
    finally:
        if cookies_file and os.path.exists(cookies_file):
            try:
                os.remove(cookies_file)
                tqdm.write(f"--> Cleaned up temp cookies: {cookies_file}")
            except OSError as e:
                tqdm.write(f"⚠️ Failed to remove temp cookies: {e}")

# Global flag for force_fresh
force_fresh = False

def main():
    """
    Main function to parse arguments and run the download process.
    """
    global force_fresh # Make force_fresh global so 'requests' downloader can see it
    
    check_and_install_packages()
    browser_path = check_and_install_chromium()
    
    file_path = 'scrapervideo_checklist.txt'
    subfolder = None
    
    force_fresh = '--fresh' in sys.argv
    debug = '--debug' in sys.argv
    
    args = [arg for arg in sys.argv[1:] if arg not in ['--fresh', '--debug']]
    
    for arg in args:
        if os.path.isfile(arg):
            file_path = arg
        elif arg and not arg.startswith('-'):
            subfolder = arg
    
    print(f"\n🚀 scrapervideo.py - VDH Mode (Smart Bypass)")
    print(f"📄 Using URL file: '{file_path}'")
    if subfolder:
        print(f"📁 Output subfolder: '{subfolder}'")
    if force_fresh:
        print("🔄 Fresh download mode enabled: will re-download existing files.")
    if debug:
        print("🔍 Debug mode enabled: Browser will be visible for webpage scraping.")
    
    if not os.path.exists(file_path):
        print(f"❌ File '{file_path}' not found."); sys.exit(1)
    
    with open(file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    unique_urls = list(dict.fromkeys(urls))
    
    download_dir = os.path.expanduser('~/ai/apps/scraper_video/output')
    if subfolder:
        download_dir = os.path.join(download_dir, subfolder)
    os.makedirs(download_dir, exist_ok=True)
    
    print(f"📊 Found {len(unique_urls)} unique URLs. Output: {download_dir}")
    
    success_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future_to_url = {executor.submit(download_video_main, url, download_dir, i, browser_path, force_fresh, debug): url for i, url in enumerate(unique_urls)}
        
        for future in tqdm(concurrent.futures.as_completed(future_to_url), total=len(unique_urls), desc="Overall Progress"):
            if future.result():
                success_count += 1
    
    print(f"\n{'='*60}")
    if len(unique_urls) > 0:
        print(f"📈 SUMMARY: {success_count}/{len(unique_urls)} successful ({success_count/len(unique_urls)*100:.1f}%)")
    else:
        print("📈 SUMMARY: No URLs to process.")
    print('='*60)
    
    if success_count < len(unique_urls):
        print("\n🔧 For failed downloads, check the error messages above.")
        print("   To force a re-download of an existing file, use the --fresh flag.")

if __name__ == "__main__":
    main()