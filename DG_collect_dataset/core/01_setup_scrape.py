import sys
import os
import time
import json
import requests
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright
import utils

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

def download_image(url, save_path):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
    except Exception:
        pass
    return False

def scrape_bing_images(query, limit, save_dir, prefix):
    print(f"--> Launching Playwright for Bing: '{query}'")
    search_url = f"https://www.bing.com/images/search?q={quote_plus(query)}&first=1"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(search_url)
        
        urls = set()
        print("--> Scrolling for images...")
        
        while len(urls) < limit:
            # Scroll down
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.5)
            
            # Click "See more" if it appears
            try:
                if page.is_visible("a.btn_seemore"):
                    page.click("a.btn_seemore")
                    time.sleep(1)
            except: pass
            
            # Extract thumbnails
            thumbnails = page.query_selector_all("a.iusc")
            for thumb in thumbnails:
                if len(urls) >= limit: break
                try:
                    m = json.loads(thumb.get_attribute("m"))
                    murl = m.get("murl")
                    if murl: urls.add(murl)
                except: pass
            
            print(f"    Found {len(urls)} images so far...")
            if len(thumbnails) == 0: break # Stop if no results

        browser.close()
        
    print(f"--> Downloading {len(urls)} images...")
    count = 0
    for i, url in enumerate(urls):
        ext = os.path.splitext(url)[1].lower()
        if ext not in ALLOWED_EXTENSIONS: ext = ".jpg"
        
        filename = f"{prefix}_{i:03d}{ext}"
        if download_image(url, save_dir / filename):
            print(f"    Downloaded: {filename}")
            count += 1
            
    print(f"✅ Downloaded {count} images.")

def run(full_name, limit, gender):
    slug = utils.slugify(full_name)
    path = utils.get_project_path(slug)
    scrape_dir = path / utils.DIRS['scrape']
    scrape_dir.mkdir(parents=True, exist_ok=True)
    
    # Load or Generate Trigger
    config = utils.load_config(slug)
    if not config or 'trigger' not in config:
        trigger = utils.gen_trigger(full_name)
    else:
        trigger = config['trigger']
        
    # Save Config
    config = {
        'prompt': full_name,
        'trigger': trigger,
        'count': limit,
        'gender': gender
    }
    utils.save_config(slug, config)
    print(f"🔑 Trigger Word: {trigger}")

    existing = [f for f in os.listdir(scrape_dir) if f.lower().endswith(tuple(ALLOWED_EXTENSIONS))]
    if len(existing) >= limit:
        print(f"✅ Found {len(existing)} images, skipping scrape.")
        return slug

    scrape_bing_images(full_name, limit, scrape_dir, slug)
    return slug