import sys
import os
import time
import json
import requests
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright
import utils

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

def download_image(url, save_path):
    try:
        # Timeout ensures we don't hang on bad links
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
    except: pass
    return False

def scrape_bing_playwright(query, limit, save_dir, prefix):
    print(f"--> Launching Playwright for Bing: '{query}'")
    # HDRSC3 form often yields better infinite scroll results
    search_url = f"https://www.bing.com/images/search?q={quote_plus(query)}&form=HDRSC3&first=1"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(search_url, timeout=60000)
        time.sleep(2)
        
        urls = set()
        stagnation_counter = 0
        
        print(f"--> Scrolling to find {limit} images...")
        
        while len(urls) < limit:
            prev_len = len(urls)
            
            # 1. Scroll to bottom
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
            # 2. Extract Images
            thumbnails = page.query_selector_all("a.iusc")
            for thumb in thumbnails:
                if len(urls) >= limit: break
                m = thumb.get_attribute("m")
                if m:
                    try:
                        data = json.loads(m)
                        img_url = data.get("murl")
                        if img_url and img_url.startswith("http"): 
                            urls.add(img_url)
                    except: pass
            
            print(f"    Found {len(urls)} unique URLs...")
            
            # 3. Handle Stagnation / Pagination
            if len(urls) == prev_len:
                stagnation_counter += 1
                
                # Attempt to click "See More" using multiple known selectors
                clicked = False
                selectors = [
                    "input[value*='See more']", # Standard input button
                    "a.see_more_btn",           # Link style
                    ".btn_seemore",             # Generic class
                    "#b_footer"                 # Sometimes clicking footer triggers load
                ]
                
                for sel in selectors:
                    try:
                        if page.is_visible(sel):
                            print(f"    Clicking '{sel}' to load more...")
                            page.click(sel, timeout=1000)
                            time.sleep(2)
                            clicked = True
                            break
                    except: pass
                
                # If we clicked, reset counter to give it a chance to load
                if clicked:
                    stagnation_counter = 0
                
                # If we tried 3 times with no growth, assume end of results
                if stagnation_counter > 3:
                    print("    ⚠️ No new images found after retries. Stopping scrape.")
                    break
            else:
                stagnation_counter = 0 # Reset if we found new images

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
            if count >= limit: break
            
    print(f"✅ Downloaded {count} images.")

def run(full_name, limit, gender, trigger_arg=None):
    slug = utils.slugify(full_name)
    path = utils.get_project_path(slug)
    scrape_dir = path / utils.DIRS['scrape']
    scrape_dir.mkdir(parents=True, exist_ok=True)
    
    if not trigger_arg:
        trigger = utils.gen_trigger(full_name)
    else:
        trigger = trigger_arg
        
    config = {
        'prompt': full_name,
        'trigger': trigger,
        'count': limit,
        'gender': gender
    }
    utils.save_config(slug, config)
    utils.update_trigger_db(slug, trigger, full_name)
    print(f"🔑 Trigger Word: {trigger}")

    existing = [f for f in os.listdir(scrape_dir) if f.lower().endswith(tuple(ALLOWED_EXTENSIONS))]
    if len(existing) >= limit:
        print(f"✅ Found {len(existing)} images, skipping scrape.")
        return slug

    scrape_bing_playwright(full_name, limit, scrape_dir, slug)
    return slug