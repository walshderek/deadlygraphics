# Script Name: core/01_setup_scrape.py
# Description: Scrapes Bing Images for the dataset.

import os
import sys
import requests
import re
import concurrent.futures
from io import BytesIO
from PIL import Image
import utils

def fetch_bing_images(query, limit):
    print(f"--> Searching Bing for: '{query}'")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    url = f"https://www.bing.com/images/async?q={query}&first=0&count={limit}&adlt=off"
    try:
        r = requests.get(url, headers=headers)
        return re.findall(r'murl&quot;:&quot;(.*?)&quot;', r.text)[:limit]
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return []

def download_worker(url, dest_dir, idx):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200: return None
        
        img = Image.open(BytesIO(r.content)).convert("RGB")
        filename = f"img_{idx:04d}.jpg"
        path = os.path.join(dest_dir, filename)
        img.save(path, "JPEG", quality=95)
        return path
    except:
        return None

def run(full_name, limit=50, gender=None):
    # 1. Setup Directories
    slug = utils.slugify(full_name)
    path = utils.get_project_path(slug)
    scrape_dir = path / utils.DIRS['scrape'] # "00_scraped"
    
    if not scrape_dir.exists():
        scrape_dir.mkdir(parents=True, exist_ok=True)

    print(f"--> Output: {scrape_dir}")

    # 2. Get URLs
    urls = fetch_bing_images(full_name, limit)
    if not urls:
        print("❌ No images found.")
        return slug

    # 3. Download
    print(f"--> Downloading {len(urls)} images...")
    downloaded = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(download_worker, u, str(scrape_dir), i) for i, u in enumerate(urls)]
        for f in concurrent.futures.as_completed(futures):
            if f.result(): downloaded += 1
    
    print(f"✅ Downloaded {downloaded} images.")
    
    # 4. Save Config
    config = {
        "name": full_name,
        "slug": slug,
        "gender": gender,
        "trigger": "ohwx", # Default, updated later
        "count": downloaded
    }
    utils.save_config(slug, config)
    
    return slug