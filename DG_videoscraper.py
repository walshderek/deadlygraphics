# DG_videoscraper_multi.py
# Authors: DeadlyGraphics, Gemini, ChatGPT (updated)
# Description: Smart video downloader. 4-Tier fallback:
#   Tier 0: Node JS PORNHUB API integration (if available)
#   Tier 1: yt-dlp first (cookies-from-browser, dump json)
#   Tier 2: Chrome sniff (undetected_chromedriver + hardened flags)
#   Tier 3: Opera sniff (existing)
#
# Usage: same as your original script.

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
            # do not exit — user may want to run other tiers
            # sys.exit(1)

def check_browser_installed(browser_name):
    if browser_name == "chrome":
        return shutil.which('google-chrome') or shutil.which('google-chrome-stable') or shutil.which('chromium') or shutil.which('chrome')
    elif browser_name == "opera":
        return shutil.which('opera') or shutil.which('opera-stable')
    return None

# ==========================================
# TIER 0: Node-based API (JustalK PORNHUB-API)
# ==========================================
def attempt_node_api(url, output_dir):
    """
    If the user has node and @justalk/pornhub-api installed, call a short node script
    to extract download URLs and return best stream + title.
    Falls back gracefully if node or package missing.
    """
    node_bin = shutil.which('node')
    if not node_bin:
        log("[Tier 0] Node.js not found. Skipping Node-based API.")
        return False

    # We'll try to run a tiny ephemeral node script that uses the package if installed.
    node_script = r"""
(async () => {
  try {
    const pornhub = require('@justalk/pornhub-api');
    const url = process.argv[1];
    const video = await pornhub.page(url, ['title','download_urls']);
    const out = { title: video.title || 'video', download_urls: video.download_urls || {}};
    console.log(JSON.stringify(out));
  } catch (e) {
    console.error("ERROR_NODE_API::"+e.message);
    process.exit(2);
  }
})();
"""
    tf = None
    try:
        tf = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.js')
        tf.write(node_script)
        tf.close()
        proc = subprocess.run([node_bin, tf.name, url], capture_output=True, text=True, timeout=40)
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        if proc.returncode != 0:
            if "Cannot find module '@justalk/pornhub-api'" in stderr:
                log("[Tier 0] @justalk/pornhub-api not installed. Install with:")
                log("  npm i @justalk/pornhub-api")
                return False
            log(f"[Tier 0] Node API error: {stderr.splitlines()[-1] if stderr else 'unknown'}")
            return False
        # parse JSON
        try:
            j = json.loads(stdout)
            # pick best quality url if available
            dls = j.get('download_urls') or {}
            # dls often keyed by quality names; pick highest by heuristics
            best_url = None
            keys = sorted(dls.keys(), reverse=True)
            for k in keys:
                val = dls[k]
                if isinstance(val, str):
                    best_url = val; break
                if isinstance(val, dict):
                    # some shapes: {url: ...}
                    candidate = val.get('url') or list(val.values())[0] if val else None
                    if candidate:
                        best_url = candidate; break
            title = j.get('title') or 'video'
            if best_url:
                log(f"[Tier 0] Found download url via Node API: {best_url[:80]}...")
                return download_file(best_url, output_dir, referer=url, title=title)
            else:
                log("[Tier 0] Node API returned no download links.")
                return False
        except Exception as e:
            log(f"[Tier 0] Failed parsing Node API output: {e}")
            return False
    except subprocess.TimeoutExpired:
        log("[Tier 0] Node API call timed out.")
        return False
    finally:
        if tf:
            try: os.remove(tf.name)
            except: pass

# ==========================================
# TIER 1: yt-dlp first (smart extraction)
# ==========================================
def attempt_yt_dlp_first(url, output_dir):
    import subprocess, shlex, shutil
    ytdlp = None
    try:
        import yt_dlp
        ytdlp = True
    except Exception:
        ytdlp = shutil.which('yt-dlp')
    if not ytdlp:
        log("[Tier 1] yt-dlp not found. Skipping.")
        return False

    # Prefer cookies from browser (if accessible)
    cookiefile = None
    cookie_args = []
    # on linux, many users use Chrome; yt-dlp supports --cookies-from-browser
    # we'll try to use that via subprocess if binary installed
    # But we will also try yt_dlp python API as fallback
    try:
        # First try command-line dump json (good for script detection)
        cmd = ['yt-dlp', '--no-warnings', '--dump-single-json', url]
        # try cookies-from-browser if available (may require system)
        cmd += ['--cookies-from-browser', 'chrome:default'] if shutil.which('yt-dlp') else []
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode == 0 and proc.stdout:
            info = json.loads(proc.stdout)
            # try to get best direct url (entries -> formats)
            formats = info.get('formats') or []
            best = None
            for f in sorted(formats, key=lambda x: (x.get('filesize') or 0, x.get('height') or 0), reverse=True):
                # prefer direct mp4/m3u8/webm
                u = f.get('url')
                if u:
                    best = u
                    break
            title = info.get('title') or 'video'
            if best:
                log(f"[Tier 1] yt-dlp found stream: {best[:80]}...")
                return download_file(best, output_dir, referer=url, title=title)
        else:
            log("[Tier 1] yt-dlp CLI dump failed; trying Python API.")
    except Exception as e:
        log(f"[Tier 1] yt-dlp dump-json error: {e}")

    # Fallback to Python API call to download directly
    try:
        import yt_dlp
        opts = {
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'format': 'bestvideo+bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            log("[Tier 1] Attempting yt-dlp full download...")
            ydl.download([url])
            return True
    except Exception as e:
        log(f"[Tier 1] yt-dlp Python API failed: {e}")
        return False

# ==========================================
# TIER 2: CHROME SNIFFER (hardened undetected)
# ==========================================
def attempt_chrome_sniff(url):
    try:
        # import with aliasing for systems where selenium-wire is present
        from seleniumwire import undetected_chromedriver as uc
    except Exception as e:
        log(f"[Tier 2] selenium-wire/undetected_chromedriver missing: {e}")
        return None, None, None

    if not check_browser_installed("chrome"):
        log("[Tier 2] Chrome not found. Skipping.")
        return None, None, None

    log(f"[Tier 2] Sniffing with Chrome: {url}")
    driver = None
    try:
        opts = uc.ChromeOptions()
        # Hardened flags to avoid privacy blocking
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--mute-audio')
        # disable headless-detection
        opts.add_argument('--headless=new')
        opts.add_argument('--disable-features=AutomationControlled,IsolateOrigins,site-per-process')
        opts.add_argument('--ignore-certificate-errors')
        opts.add_argument('--allow-running-insecure-content')
        opts.add_argument('--disable-web-security')
        opts.add_argument('--no-first-run')
        opts.add_argument('--no-default-browser-check')
        opts.add_argument('--disable-blink-features=RootLayerScrolling')
        # realistic UA
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        driver = uc.Chrome(options=opts)
        return run_vdh_logic(driver, url)
    except Exception as e:
        log(f"[Tier 2] Chrome Failed: {e}")
        return None, None, None
    finally:
        if driver:
            try: driver.quit()
            except: pass

# ==========================================
# TIER 3: OPERA SNIFFER (VPN Capable)
# ==========================================
def attempt_opera_sniff(url):
    try:
        from seleniumwire import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.opera import OperaDriverManager
        from selenium.webdriver.chrome.options import Options
    except Exception as e:
        log(f"[Tier 3] Missing selenium/opera deps: {e}")
        return None, None, None

    if not check_browser_installed("opera"):
        log("[Tier 3] Opera not found. Skipping.")
        return None, None, None

    log(f"[Tier 3] Sniffing with Opera: {url}")

    token = load_github_token()
    if token: os.environ['GH_TOKEN'] = token

    driver = None
    try:
        options = Options()
        options.add_experimental_option('w3c', True)
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        # attempt to use local user data to preserve cookies/login
        user_data = os.path.expanduser("~/.config/opera")
        if os.path.exists(user_data):
            options.add_argument(f"user-data-dir={user_data}")
        options.binary_location = check_browser_installed("opera")
        options.add_argument('--headless=new')
        # realistic UA
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        driver_path = OperaDriverManager().install()
        service = Service(driver_path)

        driver = webdriver.Chrome(service=service, options=options)
        return run_vdh_logic(driver, url)
    except Exception as e:
        log(f"[Tier 3] Opera Failed: {e}")
        return None, None, None
    finally:
        if driver:
            try: driver.quit()
            except: pass

# ==========================================
# SHARED LOGIC (improved)
# ==========================================
def run_vdh_logic(driver, url):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    # capture common video file patterns
    driver.scopes = [r'.*\.m3u8.*', r'.*\.mp4.*', r'.*\.webm.*', r'.*\.mpd.*']
    driver.get(url)
    # wait a bit longer for scripts to run (increase for heavy JS pages)
    time.sleep(6)

    # Extract Title for cleaner filename
    page_title = driver.title
    clean_title = re.sub(r'[\\/*?:"<>|]', "", page_title).strip()
    if not clean_title: clean_title = "video"
    log(f"Page Title: {clean_title}")

    def click_play(d, depth=0):
        if depth > 6: return False
        try:
            # Try different heuristics
            selectors = [
                "button[class*='play']",
                "div[class*='play']",
                "button[aria-label*='Play']",
                "video",
                "button.play",
                ".vjs-big-play-button",
            ]
            for sel in selectors:
                try:
                    elems = d.find_elements(By.CSS_SELECTOR, sel)
                    for el in elems:
                        try:
                            d.execute_script("arguments[0].scrollIntoView(true);", el)
                            d.execute_script("arguments[0].click();", el)
                            return True
                        except:
                            pass
                except:
                    pass

            # Try to call play() on any video element via JS
            try:
                r = d.execute_script("""
                    let vids = document.querySelectorAll('video');
                    if(vids.length){
                      for(let v of vids){ try{ v.muted = true; v.play(); }catch(e){} }
                      return true;
                    }
                    // shadowDOM attempt
                    let all = [...document.querySelectorAll('*')];
                    for(let el of all){
                      try{
                        if(el.shadowRoot){
                          let v = el.shadowRoot.querySelector('video');
                          if(v){ v.muted = true; v.play(); return true;}
                        }
                      }catch(e){}
                    }
                    return false;
                """)
                if r:
                    return True
            except:
                pass

            # try iframes recursively
            iframes = d.find_elements(By.TAG_NAME, "iframe")
            for frame in iframes:
                try:
                    d.switch_to.frame(frame)
                    if click_play(d, depth + 1):
                        d.switch_to.default_content()
                        return True
                    d.switch_to.parent_frame()
                except:
                    try: d.switch_to.parent_frame()
                    except: pass
        except:
            pass
        return False

    if not click_play(driver):
        log("No play button found (play attempts made).")

    log("Waiting 15s for streams...")
    time.sleep(15)

    best_stream = None
    max_size = 0

    # iterate captured requests (selenium-wire)
    for req in reversed(getattr(driver, 'requests', [])):
        try:
            if not req.response: continue
            u = req.url
            if any(ext in u for ext in ['.m3u8', '.mp4', '.webm', '.mpd']):
                # attempt to figure size
                content_len = int(req.response.headers.get('Content-Length', 0) or 0)
                if '.m3u8' in u:
                    log(f"✅ Found HLS Stream: {u[:120]}...")
                    cookies = save_cookies_safe(driver)
                    return u, cookies, clean_title
                file_size_mb = content_len / (1024 * 1024)
                if file_size_mb > max_size:
                    max_size = file_size_mb
                    best_stream = u
        except Exception:
            continue

    if best_stream and max_size > 1:  # lower threshold to catch smaller files
        log(f"✅ Found Stream ({max_size:.2f} MB): {best_stream[:120]}...")
        cookies = save_cookies_safe(driver)
        return best_stream, cookies, clean_title

    # nothing found
    return None, None, None

def save_cookies_safe(driver):
    try:
        tf = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        tf.write("# Netscape HTTP Cookie File\n")
        for c in driver.get_cookies():
            domain = c.get('domain', '')
            if not domain.startswith('.'): domain = '.' + domain
            path = c.get('path', '/')
            secure = 'TRUE' if c.get('secure', False) else 'FALSE'
            expiry = int(c.get('expiry', time.time() + 3600)) if c.get('expiry') else int(time.time() + 3600)
            name = c.get('name', '')
            value = c.get('value', '')
            if name and value:
                tf.write(f"{domain}\tTRUE\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
        tf.close()
        return tf.name
    except Exception:
        return None

def download_file(url, output_dir, cookie_file=None, referer=None, title=None):
    import yt_dlp

    # Construct safe filename
    if not title: title = "video"
    safe_name = f"{title}.%(ext)s"

    # Headers
    headers = {'Referer': referer} if referer else {}
    if "noodlemagazine" in (referer or ""):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://noodlemagazine.com/",
            "Accept": "*/*"
        }

    opts = {
        'outtmpl': os.path.join(output_dir, safe_name),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'http_headers': headers
    }
    if cookie_file: opts['cookiefile'] = cookie_file

    log(f"Downloading to: {os.path.join(output_dir, title)}")
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        log(f"Download failed: {e}")
        return False

def determine_output_dir():
    windows_drive = "/mnt/h/My Drive/AI/Downloads"
    if os.path.exists("/mnt/h"):
        if not os.path.exists(windows_drive):
            try: os.makedirs(windows_drive)
            except: return "downloads"
        return windows_drive
    return "downloads"

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

    if not urls:
        log(f"No URLs in {DEFAULT_CHECKLIST}."); sys.exit(0)

    output_dir = determine_output_dir()
    log(f"Saving to: {output_dir}")

    print(f"🚀 Processing {len(urls)} URLs...")
    for url in urls:
        print(f"\n--- Processing: {url[:140]} ---")
        # Tier 0: Node API (fast, programmatic)
        try:
            ok = attempt_node_api(url, output_dir)
            if ok:
                continue
        except Exception as e:
            log(f"[Tier 0] Exception: {e}")

        # Tier 1: yt-dlp first
        try:
            ok = attempt_yt_dlp_first(url, output_dir)
            if ok:
                continue
        except Exception as e:
            log(f"[Tier 1] Exception: {e}")

        # Tier 2: Chrome sniffing
        try:
            stream_url, cookies, title = attempt_chrome_sniff(url)
            if stream_url:
                download_file(stream_url, output_dir, cookies, referer=url, title=title)
                if cookies:
                    try: os.remove(cookies)
                    except: pass
                continue
        except Exception as e:
            log(f"[Tier 2] Exception: {e}")

        # Tier 3: Opera sniffing
        try:
            stream_url, cookies, title = attempt_opera_sniff(url)
            if stream_url:
                download_file(stream_url, output_dir, cookies, referer=url, title=title)
                if cookies:
                    try: os.remove(cookies)
                    except: pass
                continue
        except Exception as e:
            log(f"[Tier 3] Exception: {e}")

        log("❌ ALL TIERS FAILED.")

if __name__ == "__main__":
    main()
